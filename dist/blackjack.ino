#include <Keyboard.h>
#include <Mouse.h>

class Automation {
  public:
    // Constructor initializes movement speed and click delay
    Automation(int moveSpeed = 10, int clickDelay = 50) 
      : MOVE_SPEED(moveSpeed), CLICK_DELAY(clickDelay) {}

    // Initialize Mouse and Keyboard
    void begin() {
      Serial.begin(9600);
      Mouse.begin();
      Keyboard.begin();
    }

    // Reset Mouse position to the origin
    void resetToOrigin() {
      for (int i = 0; i < 100; i++) {
        Mouse.move(-MOVE_SPEED, -MOVE_SPEED);
        delay(5);
      }
    }

    // Move Mouse and perform clicks
    void moveAndClick(int xMove, int yMove, int steps, int clicks) {
      for (int i = 0; i < steps; i++) {
        Mouse.move(xMove, yMove);
        delay(10);
      }
      
      for (int i = 0; i < clicks; i++) {
        Mouse.click();
        delay(CLICK_DELAY);
      }
      
      for (int i = 0; i < steps; i++) {
        Mouse.move(-xMove, -yMove);
        delay(10);
      }
    }

    // Simulate a space key press
    void clickStart() {
      Keyboard.press(' ');
      delay(100);  // Ensure the key press is registered
      Keyboard.release(' ');
    }

    // Execute a series of slot clicks
    void clickSlot() {
      int slots[3][4] = {
        {10, 14, 20, 1},
        {10, 10, 38, 1},
        {10, 20, 11, 1}
      };
      
      for (int i = 0; i < 3; i++) {
        moveAndClick(slots[i][0], slots[i][1], slots[i][2], slots[i][3]);
        delay(500);
      }
      clickStart();
    }

    void clickSlotDe() {
      int slots[2][4] = {
        {10, 5, 75, 1},
        {10, 7, 61, 1},
      };
      
      for (int i = 0; i < 2; i++) {
        moveAndClick(slots[i][0], slots[i][1], slots[i][2], slots[i][3]);
        delay(500);
      }
      clickStart();
    }

    // Process different commands
    void processCommand(const String& command) {
      if (command == "clickslot") {
        clickSlot();
        moveAndClick(10, 13, 20, 1);
        delay(500);
        moveAndClick(10, 8, 41, 1);
        delay(500);
        moveAndClick(10, 20, 9, 1);
        delay(500);
      }
      else if (command == "clickslotde") {
        clickSlotDe();
        moveAndClick(10, 4, 75, 1);
        delay(500);
        moveAndClick(10, 5, 64, 1);
        delay(500);
      } else if (command == "startbet") {
        clickStart();
      } else if (command == "hit") {
        Keyboard.press('2');
        delay(100);  // Ensure the key press is registered
        Keyboard.release('2');
      } else if (command == "stand") {
        Keyboard.press('1');
        delay(100);  // Ensure the key press is registered
        Keyboard.release('1');
      } else if (command == "doubled") {
        Keyboard.press('4');
        delay(100);  // Ensure the key press is registered
        Keyboard.release('4');
      } else if (command == "change_table") {
        moveAndClick(10, 1, 90, 1);
        delay(1000);
        moveAndClick(10, 2, 85, 1);
        delay(1000);

        clickSlotDe();
        moveAndClick(10, 4, 75, 1);
        delay(500);
        moveAndClick(10, 5, 64, 1);
        delay(500);
        clickStart();
      } else if (command == "times_two") {
        moveAndClick(10, 3, 85, 1);
        // moveAndClick(10, 4, 75, 1);
        delay(500);
        // moveAndClick(10, 4, 69, 1);
        // delay(500);
        clickStart();
      } else if (command == "stop") {
        moveAndClick(10, 1, 90, 1);
        delay(1000);
        moveAndClick(10, 2, 85, 1);
        delay(1000);
      }
      Keyboard.releaseAll();
    }

    // End Mouse and Keyboard operations
    void end() {
      Mouse.end();
      Keyboard.end();
    }

  private:
    const int MOVE_SPEED;
    const int CLICK_DELAY;
};

// Create an instance of Automation
Automation automation;

void setup() {
  automation.begin();
}

void loop() {
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    Serial.print("Received command: ");
    Serial.println(command);

    automation.resetToOrigin();
    automation.processCommand(command);
  }
}
