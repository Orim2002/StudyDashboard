#define IR_USE_AVR_TIMER1 
#include <IRremote.h>
#include <LiquidCrystal.h>

const int IR_RECEIVE_PIN = 8;
const int BUZZER_PIN = 9; 
LiquidCrystal lcd(11, 10, 5, 4, 3, 2);
int sensorValue = 0;

enum State { IDLE, SETTING, RUNNING, DONE };
State currentState = IDLE;

// --- משתני פומודורו אוטומטי ---
int pomodoroCount = 0;
bool isWorkPhase = true;

int inputMinutes = 0;            
long workLeftSeconds = 0;
long currentPhaseSeconds = 0;
int currentWorkMinutes = 0;
unsigned long lastTickTime = 0;  

String scheduleLine1 = "Waiting for PC..";
String scheduleLine2 = "Connect Python";

byte hourglass0[8] = { B11111, B11111, B01110, B00100, B01010, B10001, B11111, B00000 }; 
byte hourglass1[8] = { B11111, B10001, B01110, B00100, B01110, B10001, B11111, B00000 }; 
byte hourglass2[8] = { B11111, B10001, B01010, B00100, B01110, B11111, B11111, B00000 }; 
byte hourglass3[8] = { B11111, B10001, B01010, B00100, B01010, B10001, B11111, B00000 };

String shortBreaks[] = {"Play Wordle!  ", "Drink Water!  ", "Stretch Legs! ", "Breathe...    "};
String longBreaks[] =  {"Brew some Moka", "Sync Goodnotes", "Protein Snack!", "Rest your eyes"};

void setup() {
  pinMode(A0, INPUT);
  Serial.begin(9600); 
  IrReceiver.begin(IR_RECEIVE_PIN, ENABLE_LED_FEEDBACK);
  pinMode(BUZZER_PIN, OUTPUT); 
  lcd.begin(16, 2);

  lcd.createChar(0, hourglass0);
  lcd.createChar(1, hourglass1);
  lcd.createChar(2, hourglass2);
  lcd.createChar(3, hourglass3);

  updateScheduleDisplay(); 
}

int decodeNumber(int code) {
  switch(code) {
    case 22: return 0; case 12: return 1; case 24: return 2;
    case 94: return 3; case 8:  return 4; case 28: return 5;
    case 90: return 6; case 66: return 7; case 82: return 8;
    case 74: return 9; default: return -1;
  }
}

void cancelTimer() {
  noTone(BUZZER_PIN);
  currentState = IDLE;
  inputMinutes = 0;
  workLeftSeconds = 0;
  currentPhaseSeconds = 0;
  currentWorkMinutes = 0;
  isWorkPhase = true; 
  pomodoroCount = 0;
  updateScheduleDisplay(); 
}

bool delayAndCheck(unsigned long ms) {
  unsigned long start = millis();
  while (millis() - start < ms) {
    if (IrReceiver.decode()) {
      int cmd = IrReceiver.decodedIRData.command;
      IrReceiver.resume(); 
      if (cmd == 69) return true;  
    }
  }
  return false;
}

void playStartSong() {
  int notes[] = {392, 262, 311, 349, 392, 262, 311, 349, 392}; 
  int durations[] = {750, 750, 375, 375, 750, 750, 375, 375, 1500}; 
  for (int i = 0; i < 9; i++) {
    tone(BUZZER_PIN, notes[i]);
    if (delayAndCheck(durations[i])) { cancelTimer(); return; } 
    noTone(BUZZER_PIN);
    if (delayAndCheck(75)) { cancelTimer(); return; }
  }
}

void playVictorySong() {
  int notes[] = {392, 392, 392, 311, 466, 392, 311, 466, 392};
  int durations[] = {750, 750, 750, 525, 225, 750, 525, 225, 1500}; 
  for (int i = 0; i < 9; i++) {
    tone(BUZZER_PIN, notes[i]);
    if (delayAndCheck(durations[i])) { cancelTimer(); return; } 
    noTone(BUZZER_PIN);
    if (delayAndCheck(75)) { cancelTimer(); return; }
  }
}

void playVictoryMelody() {
  tone(BUZZER_PIN, 523, 100);
  delay(150);
  tone(BUZZER_PIN, 659, 100);
  delay(150);
  tone(BUZZER_PIN, 784, 250);
  delay(300);
  noTone(BUZZER_PIN);
}

void updateScheduleDisplay() {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print(scheduleLine1.substring(0, 16)); 
  lcd.setCursor(0, 1);
  lcd.print(scheduleLine2.substring(0, 16));
}

void updateSettingDisplay() {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Total Work(Min):");
  lcd.setCursor(0, 1);
  lcd.print("> ");
  lcd.print(inputMinutes);
  lcd.print(":00");
}

void updateRunningDisplay() {
  int m = currentPhaseSeconds / 60;
  int s = currentPhaseSeconds % 60;
  
  lcd.setCursor(0, 0);
  String taskName;
  
  if (isWorkPhase) {
    if (scheduleLine1 == "Waiting for PC..") {
      taskName = "Deep Work...";
    } else {
      taskName = scheduleLine1.substring(0, 14);
    }
  } else {
    if (pomodoroCount % 4 == 0) {
      taskName = "Long Break!   ";
    } else {
      taskName = "Short Break!  ";
    }
  }
  
  while(taskName.length() < 14) {
    taskName += " ";
  } 
  lcd.print(taskName);
  
  lcd.setCursor(15, 0);
  lcd.write(byte(s % 4)); 
  
  lcd.setCursor(0, 1);
  lcd.print("Left: ");
  if (m < 10) lcd.print("0");
  lcd.print(m);
  lcd.print(":");
  if (s < 10) lcd.print("0");
  lcd.print(s);
  lcd.print("   "); 
}

void loop() {
  sensorValue = analogRead(A0);
  if (Serial.available() > 0) {
    String incomingData = Serial.readStringUntil('\n'); 
    incomingData.trim(); 
    int separatorIndex = incomingData.indexOf('|');     
    if (separatorIndex != -1) {
      scheduleLine1 = incomingData.substring(0, separatorIndex);
      scheduleLine2 = incomingData.substring(separatorIndex + 1);
    } else {
      scheduleLine1 = incomingData;
      scheduleLine2 = "";
    }
    if (currentState == IDLE) {
      updateScheduleDisplay();
    }
  }

  if (IrReceiver.decode()) {
    int command = IrReceiver.decodedIRData.command;
    IrReceiver.resume(); 

    static unsigned long lastIrPress = 0;
    if (millis() - lastIrPress > 500) { 
      lastIrPress = millis();

      if (command == 69) { 
        if (currentState == RUNNING || currentState == DONE || currentState == SETTING) {
          cancelTimer();
        }
      }
      else if (command == 25) {
        playVictoryMelody();
        Serial.println("DONE");
        lastIrPress = millis();
      }
      else if (command == 67) { 
        if (currentState == IDLE) {
          Serial.println("NEXT"); 
          lcd.clear();
          lcd.print("Loading next...");
        }
      }
      else if (command == 68) { 
        if (currentState == IDLE) {
          Serial.println("PREV"); 
          lcd.clear();
          lcd.print("Loading prev...");
        }
      }
      else if (command == 64) { 
        if (currentState == IDLE) { 
          Serial.println("REFRESH"); 
          lcd.clear();
          lcd.print("Syncing API...");
        } 
        else if (currentState == SETTING && inputMinutes > 0) { 
          workLeftSeconds = inputMinutes * 60;
          isWorkPhase = true;
          pomodoroCount = 0;
          
          // לוקח מקסימום 25 דקות למקטע הנוכחי, או פחות אם נשאר פחות מ-25
          currentPhaseSeconds = min(workLeftSeconds, 25L * 60L);
          currentWorkMinutes = currentPhaseSeconds / 60;
          
          currentState = RUNNING;
          lastTickTime = millis();
          lcd.clear();
          playStartSong(); 
          updateRunningDisplay(); 
        }
      }
      else {
        int number = decodeNumber(command);
        if (currentState == IDLE && number >= 0) {
          currentState = SETTING;
          inputMinutes = number;
          updateSettingDisplay();
        }
        else if (currentState == SETTING && number >= 0 && inputMinutes < 1000) {
          inputMinutes = (inputMinutes * 10) + number;
          updateSettingDisplay();
        }
      }
    }
  }

  if (currentState == RUNNING) {
    if (millis() - lastTickTime >= 1000) {
      lastTickTime += 1000;
      
      currentPhaseSeconds--;
      if (isWorkPhase) {
        workLeftSeconds--; // מקזז מזמן הלמידה הכולל רק בזמן עבודה
      }
      
      updateRunningDisplay(); 

      if (currentPhaseSeconds <= 0) {
        lcd.clear();
        lcd.setCursor(0, 0);

        if (isWorkPhase) {
          pomodoroCount++;
          Serial.print("WORK_DONE|");
          Serial.println(currentWorkMinutes);
          if (workLeftSeconds <= 0) {
            // הלמידה הסתיימה לחלוטין! (לא מתחילים הפסקה בסוף היעד)
            currentState = DONE;
            lcd.print("All Done!       ");
            lcd.setCursor(0, 1);
            lcd.print("Press OFF       ");
            playVictorySong(); 
          } else {
            // יש עוד למידה, עוברים להפסקה אוטומטית
            isWorkPhase = false;
            int r = random(0,4);
            if (pomodoroCount % 4 == 0) {
              lcd.print("Long Break!     ");
              lcd.setCursor(0, 1);
              lcd.print(longBreaks[r]);
              currentPhaseSeconds = 20L * 60L;
            } else {
              lcd.print("Short Break!    ");
              lcd.setCursor(0, 1);
              lcd.print(shortBreaks[r]);
              currentPhaseSeconds = 5L * 60L;
            }
            playVictoryMelody(); 
            delay(2000); // נותן לך 2 שניות לקרוא לפני שהמסך מתחלף
            lastTickTime = millis();
          }
        } else {
          // ההפסקה הסתיימה, חוזרים ללמוד
          isWorkPhase = true;
          // מחשב כמה לתת לסשן הבא - 25 דקות או את מה שנשאר בטוטאל
          currentPhaseSeconds = min(workLeftSeconds, 25L * 60L);
          currentWorkMinutes = currentPhaseSeconds / 60;
          
          lcd.print("Break is Over!  ");
          lcd.setCursor(0, 1);
          lcd.print("Back to Work... ");
          
          // צליל התעוררות קצר וקצבי
          tone(BUZZER_PIN, 523, 200); delay(250);
          tone(BUZZER_PIN, 1046, 400); delay(400);
          delay(1350); 
          lastTickTime = millis();
        }
      }
    }
  }
}