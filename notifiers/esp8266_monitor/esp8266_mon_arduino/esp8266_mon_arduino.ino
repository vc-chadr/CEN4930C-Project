/*
ESP8266 MQTT Monitor

This sketch subscribes to MQTT topics and displays messages on an OLED screen

Original MQTT sample code based on: https://github.com/knolleary/pubsubclient/blob/master/examples/mqtt_esp8266/mqtt_esp8266.ino

To use this sketch a config.h file must be created with your network configuration.

Example config.h file

const char* CONFIG_SSID = "ssid";
const char* CONFIG_PASSWORD = "passphrase";
const char* CONFIG_MQTT_BROKER_ADDRESS = "127.0.0.1";
const int CONFIG_MQTT_BROKER_PORT = 1883; 

*/

#include <ESP8266WiFi.h>  // Hardware | https://github.com/Heltec-Aaron-Lee/WiFi_Kit_series
#include <PubSubClient.h> // https://github.com/knolleary/pubsubclient

#include <Wire.h>         // Only needed for Arduino 1.6.5 and earlier
#include "SSD1306Wire.h"  // https://github.com/ThingPulse/esp8266-oled-ssd1306 - requires manual reset see setup()
#include "config.h"

const int MQTT_MSG_MAX_SIZE = 32;
const int MSG_BUFFER_SIZE = 50;

char mqtt_msg[MQTT_MSG_MAX_SIZE];
char msg[MSG_BUFFER_SIZE];

//SSD1306  display(0x3c, SDA, SCL, OLED_RST, GEOMETRY_128_32);
SSD1306Wire  display(0x3c, SDA, SCL, GEOMETRY_128_32);

const int PIN_BIG_BUTTON = 0;       //GPIO0 - 10k ohm pull-up resistor
const int PIN_SMALL_BUTTON = 15;    //GPIO15 - 10k ohm pull-down resistor
const int PIN_LED_RED = 14;         //GPIO14
const int PIN_LED_GREEN = 12;       //GPIO12
const int PIN_LED_BLUE = 13;        //GPIO13
const int PIN_RST = 16;             //GPIO16 OLED reset
/* Unused PINS on Heltec ESP8266 controller
const int PIN_NOT_USED0 = 2;        //GPIO2
const int PIN_NOT_AVAILABLE0 = 1;   //GPIO1 Tx
const int PIN_NOT_AVAILABLE1 = 3;   //GPIO3 Rx
const int PIN_NOT_AVAILABLE2 = 4;   //GPIO4 SDA
const int PIN_NOT_AVAILABLE3 = 5;   //GPIO5 SCL
*/

const int ALERT_MAX_TIME = 25000;
int alert_active = 0;
long alert_start_time = 0;

boolean big_button_state = HIGH;
boolean small_button_state = LOW;

WiFiClient espClient;
PubSubClient client(espClient);


void mqtt_callback(char* topic, byte* payload, unsigned int length) {
  Serial.print("Message arrived [");
  Serial.print(topic);
  Serial.print("] ");

  for (int i = 0; i < length && i < MQTT_MSG_MAX_SIZE; i++) {
    Serial.print((char)payload[i]);
    mqtt_msg[i] = ((char)payload[i]);
  }
  mqtt_msg[MQTT_MSG_MAX_SIZE] = 0;

  snprintf (msg, 50, " Time: %ld", millis());
  Serial.println(msg);
  Serial.println();  

  display.clear();
  display.setFont(ArialMT_Plain_10);
  display.drawString(0,0,topic);
  //display.drawString(116,0,"M");
  
  display.setFont(ArialMT_Plain_16);
  display.drawString(0,10,mqtt_msg);
  
  display.display();

  alert_start();

  // Switch on the LED if an 1 was received as first character
  /*
  if ((char)payload[0] == '1') {
    digitalWrite(BUILTIN_LED, LOW);   // Turn the LED on (Note that LOW is the voltage level
    // but actually the LED is on; this is because
    // it is active low on the ESP-01)
  } else {
    digitalWrite(BUILTIN_LED, HIGH);  // Turn the LED off by making the voltage HIGH
  }
  */
}

void alert_start() {
  Serial.println("Start Alert");
  alert_active = 1;
  alert_start_time = millis();
  digitalWrite(PIN_LED_GREEN, HIGH);  
}

void alert_stop() {
  Serial.println("Stop Alert");
  alert_active = 0;
  digitalWrite(PIN_LED_RED, LOW);
  digitalWrite(PIN_LED_GREEN, LOW); 
  digitalWrite(PIN_LED_BLUE, LOW);

  display.clear();
  display.display();
}

void display_basic_message(const char *msg)
{
  display.clear();
  display.drawString(0,0,msg);
  display.display();
}

boolean is_button_pressed(boolean &last, boolean triggerOnLowToHigh, int button_pin)
{
  boolean current = digitalRead(button_pin);
  if (last != current) {
    // make sure pin state is stable and is still different than last state
    delay(5);
    current = digitalRead(button_pin);
    
    if (last != current) {      
      last = current;
      if ((triggerOnLowToHigh == HIGH && current == HIGH) ||
          (triggerOnLowToHigh == LOW && current == LOW)) {
        return true;
      }
    }    
  }
  return false;
}

void reconnect() {
  // Loop until we're reconnected
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    display_basic_message("Attempting MQTT connection...");
    // Create a random client ID
    String clientId = "ESP8266Monitor-";
    clientId += String(random(0xffff), HEX);
    // Attempt to connect
    if (client.connect(clientId.c_str())) {
      Serial.println("connected");
      display.drawString(0,10,"... connected");
      display.drawString(0,20,WiFi.localIP().toString().c_str());
      display.display();

      // Once connected, publish an announcement...
      client.publish("hm/test/esp8266", "ESP8266 monitor online");
      // ... and resubscribe
      client.subscribe("hm/#");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      display_basic_message("Failed, trying again in 5 seconds");
      // Wait 5 seconds before retrying
      delay(5000);
    }
  }
}

void setup_wifi() {
  delay(10);
  // We start by connecting to a WiFi network
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(CONFIG_SSID);

  display_basic_message("Connecting");

  WiFi.begin(CONFIG_SSID, CONFIG_PASSWORD);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  randomSeed(micros());

  Serial.println("");
  Serial.println("WiFi connected");
  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());

  display_basic_message("WiFi connected");
  display.drawString(0,10,WiFi.localIP().toString().c_str());
  display.display();
}

void setup() {
  pinMode(PIN_LED_RED, OUTPUT);
  pinMode(PIN_LED_GREEN, OUTPUT);
  pinMode(PIN_LED_BLUE, OUTPUT);  
  pinMode(PIN_BIG_BUTTON, INPUT);
  pinMode(PIN_SMALL_BUTTON, INPUT);
  pinMode(PIN_RST, OUTPUT);

  // manually reset OLED display
  digitalWrite(PIN_RST, LOW);
  delay(50);
  digitalWrite(PIN_RST, HIGH);

  display.init();
  display.flipScreenVertically();
  display.setFont(ArialMT_Plain_10);

  display_basic_message("Initializing...");
  
  Serial.begin(115200);
  setup_wifi();
  client.setServer(CONFIG_MQTT_BROKER_ADDRESS, CONFIG_MQTT_BROKER_PORT);
  client.setCallback(mqtt_callback);
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  if (alert_active > 0) {
    //static long now = millis();
    if ((millis() - alert_start_time) > ALERT_MAX_TIME) {
      alert_stop();
    }
  }

  if (is_button_pressed(big_button_state, false, PIN_BIG_BUTTON))
  {
    Serial.println("BIG BUTTON DOWN");
    client.publish("hm/test/esp8266", "ESP8266 Monitor BIG BUTTON");
  }

  if (is_button_pressed(small_button_state, true, PIN_SMALL_BUTTON))
  {
    Serial.println("SMALL BUTTON DOWN");
    client.publish("hm/test/esp8266", "ESP8266 Monitor test message");
  }  
}
