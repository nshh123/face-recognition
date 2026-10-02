/*
 ==============================================================================
  AI + IoT Final Project: Face Recognition Access & Security Monitor (ESP32)
  Course: AI + IoT Final Week - AUCA Software Innovation Center
 ==============================================================================
  Hardware Components:
  - ESP32 Development Board
  - 0.96" I2C OLED Display (SSD1306 128x64)
  - 1x Green LED (Authorized Face indicator) + 220 Ohm resistor
  - 1x Red LED (Intruder Alert indicator) + 220 Ohm resistor
  - 1x Active Buzzer (Security Alert siren & Welcome beep)
  - 1x SG90 Micro Servo (Door lock mechanism: 0° Locked, 90° Open)
  - 1x Push Button (Manual Reset / Door Lock button)

  Pinout Wiring:
  - OLED Display:
      VCC -> 3.3V
      GND -> GND
      SCL -> GPIO 22
      SDA -> GPIO 21
  - Green LED:
      Anode (+) -> GPIO 18 -> [220R Resistor] -> LED -> Cathode (-) -> GND
  - Red LED:
      Anode (+) -> GPIO 19 -> [220R Resistor] -> LED -> Cathode (-) -> GND
  - Active Buzzer:
      Positive (+) -> GPIO 5
      Negative (-) -> GND
  - SG90 Servo:
      Signal (Orange/Yellow) -> GPIO 13
      VCC (Red)              -> 5V (or 3.3V)
      GND (Brown)            -> GND
  - Reset Push Button:
      One leg -> GPIO 4
      Other leg -> GND (Uses internal INPUT_PULLUP)
 ==============================================================================
*/

#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <ArduinoJson.h>
#include <ESP32Servo.h>

// ---------------------------------------------------------------------------
// Network Configuration
// (Connect ESP32 to phone hotspot or laptop mobile hotspot)
// ---------------------------------------------------------------------------
const char* WIFI_SSID     = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// Laptop IP address from `ipconfig` (running server.py on port 8000)
const char* BACKEND_HOST = "http://192.168.1.100:8000";

// ---------------------------------------------------------------------------
// Pin Definitions
// ---------------------------------------------------------------------------
#define PIN_LED_GREEN  18
#define PIN_LED_RED    19
#define PIN_BUZZER     5
#define PIN_SERVO      13
#define PIN_BUTTON_CLR 4

// ---------------------------------------------------------------------------
// OLED Display Setup (I2C SSD1306 128x64)
// ---------------------------------------------------------------------------
#define SCREEN_WIDTH  128
#define SCREEN_HEIGHT 64
#define OLED_RESET    -1
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

// ---------------------------------------------------------------------------
// Actuators
// ---------------------------------------------------------------------------
Servo doorServo;
const int SERVO_LOCKED = 0;    // 0 degrees = Closed door
const int SERVO_OPEN   = 90;   // 90 degrees = Open door

// ---------------------------------------------------------------------------
// Tracking State
// ---------------------------------------------------------------------------
String lastName = "--";
String lastStatus = "idle";
bool lastDoorOpen = false;
unsigned long lastPollTime = 0;
const unsigned long POLL_INTERVAL_MS = 350; // Poll backend every 350ms

void showOledScreen(const String& mainText, const String& subText, bool isAlert) {
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);

  // Top Title Bar
  display.setTextSize(1);
  display.setCursor(14, 2);
  display.print("AI FACE MONITOR");
  display.drawLine(0, 12, SCREEN_WIDTH, 12, SSD1306_WHITE);

  // Main Display (Name or Alert)
  display.setTextSize(2);
  int16_t x1, y1;
  uint16_t w, h;
  display.getTextBounds(mainText, 0, 0, &x1, &y1, &w, &h);
  int cursorX = max(0, (SCREEN_WIDTH - (int)w) / 2);
  display.setCursor(cursorX, 22);
  display.print(mainText);

  // Subtitle / Status
  display.drawLine(0, 48, SCREEN_WIDTH, 48, SSD1306_WHITE);
  display.setTextSize(1);
  display.getTextBounds(subText, 0, 0, &x1, &y1, &w, &h);
  int subX = max(0, (SCREEN_WIDTH - (int)w) / 2);
  display.setCursor(subX, 52);
  display.print(subText);

  display.display();
}

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("\n--- Initializing AI Face Recognition Monitor (ESP32) ---");

  // Configure Pins
  pinMode(PIN_LED_GREEN, OUTPUT);
  pinMode(PIN_LED_RED, OUTPUT);
  pinMode(PIN_BUZZER, OUTPUT);
  pinMode(PIN_BUTTON_CLR, INPUT_PULLUP);

  digitalWrite(PIN_LED_GREEN, LOW);
  digitalWrite(PIN_LED_RED, LOW);
  digitalWrite(PIN_BUZZER, LOW);

  // Attach Servo
  doorServo.attach(PIN_SERVO);
  doorServo.write(SERVO_LOCKED);

  // Initialize I2C OLED
  Wire.begin(21, 22); // SDA = 21, SCL = 22
  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println("SSD1306 OLED initialization failed!");
  } else {
    showOledScreen("STARTING", "CONNECTING WIFI", false);
  }

  // Connect to Wi-Fi
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Connecting to WiFi: ");
  Serial.println(WIFI_SSID);

  int retries = 0;
  while (WiFi.status() != WL_CONNECTED && retries < 25) {
    delay(400);
    Serial.print(".");
    retries++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi Connected! IP Address: ");
    Serial.println(WiFi.localIP());
    showOledScreen("READY", "STAND BEFORE CAM", false);
    // Short boot chirp
    digitalWrite(PIN_BUZZER, HIGH);
    delay(80);
    digitalWrite(PIN_BUZZER, LOW);
  } else {
    Serial.println("\nWiFi Connection Failed! Check SSID/Password.");
    showOledScreen("NO WIFI", "CHECK CREDENTIALS", true);
  }
}

void handleClearButton() {
  // Push button pulls pin to LOW when pressed
  if (digitalRead(PIN_BUTTON_CLR) == LOW) {
    delay(50); // debounce
    if (digitalRead(PIN_BUTTON_CLR) == LOW) {
      Serial.println(">> [PHYSICAL BUTTON PRESSED] Resetting state to Cloud...");
      if (WiFi.status() == WL_CONNECTED) {
        HTTPClient http;
        String url = String(BACKEND_HOST) + "/clear";
        http.begin(url);
        http.addHeader("Content-Type", "application/json");
        int code = http.POST("{}");
        Serial.printf("POST /clear response code: %d\n", code);
        http.end();
      }
      
      // Local immediate reset
      digitalWrite(PIN_LED_GREEN, LOW);
      digitalWrite(PIN_LED_RED, LOW);
      digitalWrite(PIN_BUZZER, LOW);
      doorServo.write(SERVO_LOCKED);
      showOledScreen("LOCKED", "SYSTEM RESET", false);

      while (digitalRead(PIN_BUTTON_CLR) == LOW) {
        delay(10);
      }
    }
  }
}

void pollBackendState() {
  if (WiFi.status() != WL_CONNECTED) return;

  HTTPClient http;
  String url = String(BACKEND_HOST) + "/state";
  http.begin(url);
  http.setTimeout(1200);

  int httpCode = http.GET();
  if (httpCode == HTTP_CODE_OK) {
    String payload = http.getString();
    StaticJsonDocument<1024> doc;
    DeserializationError error = deserializeJson(doc, payload);

    if (!error) {
      String name = doc["name"] | "--";
      String status = doc["status"] | "idle";
      float confidence = doc["confidence"] | 0.0;
      bool doorOpen = doc["door_open"] | false;
      int ledG = doc["led_green"] | 0;
      int ledR = doc["led_red"] | 0;
      int buzz = doc["buzzer"] | 0;

      // Update Actuators
      digitalWrite(PIN_LED_GREEN, ledG ? HIGH : LOW);
      digitalWrite(PIN_LED_RED,   ledR ? HIGH : LOW);
      doorServo.write(doorOpen ? SERVO_OPEN : SERVO_LOCKED);

      // Handle Buzzer sound
      if (buzz) {
        // Intermittent security alert buzz
        digitalWrite(PIN_BUZZER, (millis() / 200) % 2 == 0 ? HIGH : LOW);
      } else {
        digitalWrite(PIN_BUZZER, LOW);
      }

      // Update OLED Display when state transitions
      if (name != lastName || status != lastStatus || doorOpen != lastDoorOpen) {
        lastName = name;
        lastStatus = status;
        lastDoorOpen = doorOpen;

        if (status == "authorized") {
          String sub = "WELCOME (" + String((int)(confidence * 100)) + "%)";
          showOledScreen(name, sub, false);
          // Welcome chirp
          digitalWrite(PIN_BUZZER, HIGH);
          delay(120);
          digitalWrite(PIN_BUZZER, LOW);
        } else if (status == "alert") {
          showOledScreen("ALERT!", "ACCESS DENIED", true);
        } else if (status == "cleared") {
          showOledScreen("RESET", "DOOR LOCKED", false);
        } else {
          showOledScreen("SCANNING", "LOOK AT CAMERA", false);
        }
      }
    }
  } else {
    Serial.printf("HTTP GET failed with code: %d\n", httpCode);
  }
  http.end();
}

void loop() {
  handleClearButton();

  unsigned long currentMillis = millis();
  if (currentMillis - lastPollTime >= POLL_INTERVAL_MS) {
    lastPollTime = currentMillis;
    pollBackendState();
  }
}
