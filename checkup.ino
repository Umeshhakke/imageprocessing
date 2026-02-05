#include <WiFi.h>
#include <WebServer.h>

// ---------------- WIFI ----------------
const char* ssid = "ESP32_HOTSPOT";
const char* password = "12345678";

// ---------------- SERVER ----------------
WebServer server(80);

// ---------------- PINS ----------------
#define RAIN_PIN 34

// L298N Motor Driver Pins
#define IN1 26
#define IN2 27
#define EN1 25

#define IN3 14
#define IN4 12
#define EN2 13

// ---------------- VARIABLES ----------------
bool isRaining = false;

String motorStatus = "STOPPED";   // STOPPED / COVERING / UNCOVERING
String coverState  = "OPEN";      // OPEN / CLOSED / MOVING

int rainThreshold = 2000;

unsigned long motorStartTime = 0;
const unsigned long MOTOR_DURATION = 5000; // 5 sec

// ---------------- MODE ----------------
enum ControlMode { AUTO_MODE, MANUAL_MODE };
ControlMode controlMode = AUTO_MODE;

// ---------------- MOTOR FUNCTIONS ----------------
void stopMotors() {
  digitalWrite(IN1, LOW);
  digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW);
  digitalWrite(IN4, LOW);

  digitalWrite(EN1, HIGH);
  digitalWrite(EN2, HIGH);

  motorStatus = "STOPPED";
  Serial.println("[MOTOR] STOPPED");
}

void startCover() {
  if (coverState == "CLOSED" || motorStatus != "STOPPED") return;
  stopMotors();        
  delay(100);  
  
  coverState = "MOVING";
  motorStatus = "COVERING";
  motorStartTime = millis();

  digitalWrite(IN1, HIGH);
  digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW);
  digitalWrite(IN4, HIGH);

  digitalWrite(EN1, HIGH);
  digitalWrite(EN2, HIGH);

  Serial.println("[MOTOR] COVERING");
}

void startUncover() {
  if (coverState == "OPEN" || motorStatus != "STOPPED") return;

  stopMotors();        
  delay(100);  

  coverState = "MOVING";
  motorStatus = "UNCOVERING";
  motorStartTime = millis();

  digitalWrite(IN1, LOW);
  digitalWrite(IN2, HIGH);
  digitalWrite(IN3, HIGH);
  digitalWrite(IN4, LOW);

  digitalWrite(EN1, HIGH);
  digitalWrite(EN2, HIGH);

  Serial.println("[MOTOR] UNCOVERING");
}

// ---------------- HTTP HANDLERS ----------------
void handleStatus() {
  int rainValue = analogRead(RAIN_PIN);
  isRaining = rainValue < rainThreshold;

  // EXACT FORMAT REQUIRED BY ANDROID APP
  String response =
    "RAIN=" + String(isRaining ? "YES" : "NO") +
    ",COVER=" + coverState +
    ",MOTOR=" + motorStatus +
    ",MODE=" + String(controlMode == AUTO_MODE ? "AUTO" : "MANUAL");

  server.send(200, "text/plain", response);
}

void handleReceive() {
  if (!server.hasArg("data")) {
    server.send(400, "text/plain", "NO DATA");
    return;
  }

  String cmd = server.arg("data");
  cmd.toUpperCase();

  if (cmd == "MODE_AUTO") {
    controlMode = AUTO_MODE;
    Serial.println("[MODE] AUTO");
  }
  else if (cmd == "MODE_MANUAL") {
    controlMode = MANUAL_MODE;
    Serial.println("[MODE] MANUAL");
  }
  else if (controlMode == MANUAL_MODE) {
    if (cmd == "COVER") startCover();
    else if (cmd == "UNCOVER") startUncover();
  }

  server.send(200, "text/plain", "OK");
}

// ---------------- SETUP ----------------
void setup() {
  Serial.begin(115200);
  delay(1000);

  pinMode(RAIN_PIN, INPUT);

  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
  pinMode(IN3, OUTPUT);
  pinMode(IN4, OUTPUT);

  // ESP32 CORE v3.x PWM
  pinMood(EN1, OUTPUT);
  pinMode(EN2, OUTPUT);

  stopMotors();

  WiFi.softAP(ssid, password);
  Serial.print("ESP32 AP IP: ");
  Serial.println(WiFi.softAPIP());

  server.on("/status", HTTP_GET, handleStatus);
  server.on("/send", HTTP_POST, handleReceive);
  server.begin();

  Serial.println("HTTP SERVER STARTED");
}

// ---------------- LOOP ----------------
void loop() {
  server.handleClient();

  // ---- Motor timeout ----
  if (motorStatus != "STOPPED" &&
      millis() - motorStartTime >= MOTOR_DURATION) {

    if (motorStatus == "COVERING") coverState = "CLOSED";
    else if (motorStatus == "UNCOVERING") coverState = "OPEN";

    stopMotors();
  }

  // ---- AUTO MODE RAIN LOGIC ----
  if (controlMode == AUTO_MODE && motorStatus == "STOPPED") {
    int rainValue = analogRead(RAIN_PIN);
    bool rainNow = rainValue < rainThreshold;

    if (rainNow && coverState == "OPEN") {
      startCover();
    }
    else if (!rainNow && coverState == "CLOSED") {
      startUncover();
    }
  }
}