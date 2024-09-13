from datetime import datetime
import sys
import time
import cv2
import numpy as np
import pyautogui
import threading
import ttkbootstrap as tb
from ttkbootstrap.constants import *
import arduino as ards
from tkinter import messagebox
import database as db
from tkinter import scrolledtext
import threading
import mss

now = datetime.now()
formatted_now = now.strftime("%Y%m%d%H%M%S")
data_saved = False
betting_stop = False
detection_thread = None

class ArduinoPort:
    def __init__(self, root):
        # Create the ttkbootstrap-themed window
        self.root = root
        self.root.title("BlackJack")

        # Port frame
        self.port_frame = tb.LabelFrame(self.root, padding=7, text="Available COM Ports")
        self.port_frame.grid(row=0, column=0, sticky="nsew", padx=10)

        # List available COM ports
        self.ports_list = ards.list_ports()

        self.com_entry = tb.Combobox(self.port_frame, values=self.ports_list, width=10)
        self.com_entry.grid(row=0, column=0, sticky="w", padx=5)

        # Buttons
        self.connect_button = tb.Button(self.port_frame, text="Connect", command=self.select_port, width=12)
        self.connect_button.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        self.disconnect_button = tb.Button(self.port_frame, text="Disconnect", command=self.disconnect, bootstyle="danger", width=12)
        self.disconnect_button.grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.disconnect_button.grid_remove()  # Initially hidden

        self.upload_button = tb.Button(self.port_frame, text="Upload", command=ards.upload_code, state=DISABLED, width=9)
        self.upload_button.grid(row=0, column=3, padx=5, pady=5, sticky="w")

        self.reports_button = tb.Button(self.port_frame, text="Reports", width=9, bootstyle="success")
        self.reports_button.grid(row=0, column=4, padx=5, pady=5, sticky="w")

    def select_port(self):
        selected_port = self.com_entry.get().strip()
        if not selected_port:
            print(f"COM port not found. Please try again.")
            messagebox.showerror("Error", f"COM port not found. Please try again.")
        else:
            if ards.init_serial(selected_port):
                messagebox.showinfo("Info", f"Connected to {selected_port}.")
                self.connect_button.grid_remove()
                self.disconnect_button.grid()
                self.upload_button['state'] = 'normal'
            else:
                print(f"Failed to connect to {selected_port}. Please check the connection.")
                messagebox.showerror("Error", f"Failed to connect to {selected_port}. Please check the connection.")

    def disconnect(self):
        if messagebox.askokcancel("Warning", "Are you sure you want to disconnect?"):
            ards.close_serial()
            self.disconnect_button.grid_remove()
            self.connect_button.grid()
            self.upload_button['state'] = 'disabled'

class CardsDetector:
    def __init__(self, frame_config):
        # Coordinates and size of the regions
        self.stop_betting = False  # This should be a class attribute now
        self.detection_thread = None  # Use a class attribute for the thread
        self.previous_sums = {}
        self.root = root

        self.regions = {
            'Dealer': (427, 117, 170, 42),
            'Player A': (93, 247, 170, 42),
            'Player B': (262, 287, 170, 42),
            'Player C': (426, 305, 170, 42),
            'Player D': (599, 287, 170, 42),
            'Player E': (772, 247, 170, 42),
        }

        # Define suits and values
        self.suits = ['Diamonds', 'Clubs', 'Hearts', 'Spades']
        self.values = {'2': '2', '3': '3', '4': '4', '5': '5', '6': '6', '7': '7', '8': '8', '9': '9', '10': '10', 'J': 'J', 'Q': 'Q', 'K': 'K', 'A': 'A'}
        self.card_values = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 10, 'J': 10, 'Q': 10, 'K': 10, 'A': 11}
        self.hi_lo_values = {'2': 1, '3': 1, '4': 1, '5': 1, '6': 1, '7': 0, '8': 0, '9': 0, '10': -1, 'J': -1, 'Q': -1, 'K': -1, 'A': -1}

        # Load the template images
        self.templates = {
            f'{name}_{suit}': cv2.imread(f'assets/cards/{name.lower()}/{name.lower()}{suit.lower()}.png', 0)
            for name in self.values.values() for suit in self.suits
        }

        # Check if all templates were loaded successfully
        for key, template in self.templates.items():
            if template is None:
                raise FileNotFoundError(f"Template image for '{key}' not found.")

        # Frame for the card detector view
        frame_region = tb.LabelFrame(frame_config, padding=10, text="Card Detector View")
        frame_region.grid(row=0, column=0, sticky="news", padx=10, pady=5)

        # Initialize dictionaries for labels and sum labels
        self.labels = {}
        self.sum_labels = {}
        self.outcome_labels = {}
        row = 0

        # Loop through the regions and create the necessary labels and frames
        for region_name in self.regions.keys():
            frame = tb.Frame(frame_region, padding=5)
            frame.grid(row=row, column=0, sticky=W)

            label_title = tb.Label(frame, text=f"{region_name}", anchor=W)
            label_title.grid(row=0, column=0, sticky=W)

            label_value = tb.Label(frame, text="No card detected", anchor=W)
            label_value.grid(row=1, column=0, sticky=W)

            sum_label = tb.Label(frame, text="Sum: 0", anchor=W)
            sum_label.grid(row=2, column=0, sticky=W)

            outcome_frame = tb.Frame(frame_region, padding=5)
            outcome_frame.grid(row=row, column=1, sticky=N)

            out_label = tb.Label(outcome_frame, text="Outcome", anchor=W)
            out_label.grid(row=0, column=0, sticky=W)

            outcome_label = tb.Label(outcome_frame, text="None", anchor=W)
            outcome_label.grid(row=1, column=0, sticky=W)

            self.labels[region_name] = label_value
            self.sum_labels[region_name] = sum_label
            self.outcome_labels[region_name] = outcome_label
            row += 1

    def capture_region(self, region):
        """Capture the region of the screen for template matching."""
        x, y, w, h = region
        screenshot = pyautogui.screenshot(region=(x, y, w, h))
        img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return gray_img

    def check_cards_in_region(self, region, gray_img):
        """Perform template matching for cards in a region."""
        detected_values = set()
        region_height, region_width = gray_img.shape[:2]

        for card_name, template in self.templates.items():
            if template is None:
                continue  # Skip if the template wasn't loaded successfully
            h, w = template.shape[:2]
            if region_height < h or region_width < w:
                continue
            for scale in np.linspace(0.9, 2.2, 10):
                scaled_template = cv2.resize(template, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
                if scaled_template.shape[0] > region_height or scaled_template.shape[1] > region_width:
                    continue
                result = cv2.matchTemplate(gray_img, scaled_template, method=cv2.TM_CCOEFF_NORMED)
                _, max_val, _, max_loc = cv2.minMaxLoc(result)
                if max_val >= 0.88:
                    value, suit_initial = card_name.split('_')
                    detected_values.add(f"{value}{suit_initial[0].upper()}")
                    top_left = max_loc
                    bottom_right = (top_left[0] + scaled_template.shape[1], top_left[1] + scaled_template.shape[0])
                    cv2.rectangle(gray_img, top_left, bottom_right, (0, 255, 0), 2)
                    break 
        return list(detected_values)

    def check_all_cards(self):
        found_cards = {}
        for region_name, region in self.regions.items():
            gray_img = self.capture_region(region)
            card_values = self.check_cards_in_region(region, gray_img)
            if card_values:
                found_cards[region_name] = card_values
        return found_cards

    def sum_cards(self, region_name, detected_cards):
        """Calculate the sum of detected cards in the region and decide action."""
        total_sum = 0
        aces_count = 0

        # Calculate the total sum and handle Aces
        for card in detected_cards.get(region_name, []):
            value = card[:-1]  # Assume the last character is the suit and remove it
            card_value = self.card_values.get(value, 0)  # Get the card value from card_values dictionary

            if value == 'A':
                aces_count += 1
            total_sum += card_value

        while total_sum > 21 and aces_count > 0:
            total_sum -= 10
            aces_count -= 1

        dealer_sum = dealer_sum = self.previous_sums.get("Dealer", 0)
        status = self.status_label.cget("text")

        if status.startswith("Status:") and region_name in ["Player D", "Player E"]:
            prev_sum = self.previous_sums.get(region_name)

            # Only act if the sum has changed
            if prev_sum != total_sum:
                print(f"Region: {region_name}, Sum : {total_sum}")
                print(f"Region: Dealer, Sum: {dealer_sum}")

                # Default command
                command = 'stand'
                print_message = "Higher Numbers"

                # Determine command based on total_sum and dealer_sum
                if total_sum == 11 or (total_sum == 10 and dealer_sum <= 9) or (total_sum == 9 and 3 <= dealer_sum <= 6):
                    command = 'doubled'
                    print_message = "Double the bet"
                elif (total_sum == 10 and dealer_sum >= 10) or (total_sum == 9 and 2 >= dealer_sum >= 7):
                    command = 'hit'
                    print_message = "Total sum {} and dealer sum {}".format(total_sum, dealer_sum)
                elif total_sum == 12 and dealer_sum >= 7:
                    command = 'hit'
                    print_message = "Total sum 12 and dealer sum greater than 7"
                elif total_sum == 12 and dealer_sum <= 3:
                    command = 'hit'
                    print_message = "Total sum 12 and dealer sum less than 3"
                elif 13 <= total_sum <= 15 and dealer_sum >= 7:
                    command = 'hit'
                    print_message = "Total sum between 13 and 16 and dealer sum greater than 6"
                elif total_sum <= 10:
                    command = 'hit'
                    print_message = "Total sum less than 8"
                elif total_sum == 21: 
                    command = ''
                    print_message = "Got 21"
                elif total_sum > 21: 
                    command = ''
                    print_message = "Busted"

                # Handle previous sum condition for total_sum == 11, 10, or 9
                if command == 'doubled' and prev_sum is not None and prev_sum <= 8:
                    command = 'hit'
                    print_message = "Previous sum was less than 8"

                print(print_message)
                ards.send_command(command)
                time.sleep(.5)

            # Update the previous sum for this region
            self.previous_sums[region_name] = total_sum

        # Ensure dealer_sum is also updated
        if region_name == "Dealer":
            self.previous_sums["Dealer"] = total_sum

        return total_sum
    
    def martin_system(self, detected_cards):
        """Determine the real-time outcome based on Player E and dealer sums."""
        outcome = None
        sum_label_text = self.sum_labels["Player E"].cget("text")
        player_e_sum = int(sum_label_text.split("Sum: ")[-1].strip()) if "Sum: " in sum_label_text else 0

        dealer_sum = self.sum_cards("Dealer", detected_cards)

        # Determine the outcome based on real-time sum comparison
        if dealer_sum > player_e_sum and dealer_sum <= 21:
            outcome = "Loss"
        elif player_e_sum > 21:
            outcome = "Loss"
        elif dealer_sum > 21:
            if player_e_sum > 21:
                outcome = "Loss"
            outcome = "Win"
        elif player_e_sum > 21:
            outcome = "Loss"
        elif dealer_sum == player_e_sum:
            outcome = "Tie"
        else:
            outcome = "Win"

        return outcome

    def update_count_from_treeview(self, treeview):
        """Update the running count based on card values in the Treeview."""
        running_count = 0
        for item in treeview.get_children():
            row_data = treeview.item(item, 'values')  # Get the values for each row
            cards = row_data[1].strip()  # Assuming the cards are in the second column (index 1)

            if cards:  # Check if the cards string is not empty
                # Split the cards in case there are multiple cards in a single cell (e.g., "2H, 3S")
                for card in cards.split(', '):
                    if card:  # Ensure the card string is not empty
                        value = card[:-1].strip()  # Extract the value part and trim whitespace (e.g., '2', 'A')
                        running_count += self.hi_lo_values.get(value, 0)  # Use get to avoid KeyError for unexpected values

        return running_count

class CardsCounting(CardsDetector):
    def __init__(self, frame_config):
        super().__init__(frame_config)
        self.status_region = {
            'Start': (805, 533, 50, 49), 
            'Reset': (703, 45, 60, 60),
            'Chips D': (602, 422, 164, 69), 'Chips E': (771, 381, 164, 69),
            'Arrow A': (150, 125, 54, 82), 'Arrow B': (317, 167, 54, 82), 'Arrow C': (487, 186, 54, 82),'Arrow D': (655, 168, 54, 82), 'Arrow E': (824, 126, 54, 82),
            'Slot A': (137, 387, 80, 80), 'Slot B': (304, 425, 80, 80), 'Slot C': (474, 444, 80, 80), 'Slot D': (642, 427, 80, 80), 'Slot E': (810, 386, 80, 80),
            # 'Player A': (106, 223, 140, 40), 'Player B': (275, 263, 140, 40), 'Player C': (442, 281, 140, 40), 'Player D': (611, 264, 140, 40), 'Player E': (783, 223, 140, 40),
            'Blackjack': (783, 223, 140, 40),
            'Win E': (784, 294, 130, 45), 'Loss E': (802, 294, 105, 45), 'Tie E': (802, 294, 105, 45), 
            'Bust E': (783, 223, 140, 40)
        }

        self.status_templates = {
            'Start': cv2.imread('assets/status/start.png', 0),
            'Arrow': cv2.imread('assets/status/arrow.png', 0),
            'Reset': cv2.imread('assets/status/reset.png', 0),
            'Slot': cv2.imread('assets/status/slots.png', 0),
            'Chips': cv2.imread('assets/status/chips.png', 0),
            'Blackjack': cv2.imread('assets/status/blackjack.png', 0),
            'Win': cv2.imread('assets/status/win.png', 0),
            'Loss': cv2.imread('assets/status/loss.png', 0),
            'Tie': cv2.imread('assets/status/tie.png', 0),
            'Bust': cv2.imread('assets/status/bust.png', 0)
        }

        self.frame_count = tb.LabelFrame(frame_config, padding=10, text="Card Counting")
        self.frame_count.grid(row=0, column=1, sticky="news", padx=10, pady=5)

        # Treeview setup for card counting
        self.treeview = tb.Treeview(self.frame_count, columns=("hand", "cards", "sum"), show="headings")
        self.treeview.heading("hand", text="Hand", anchor=W)
        self.treeview.heading("cards", text="Cards", anchor=W)
        self.treeview.heading("sum", text="Sum", anchor=W)
        self.treeview.column("hand", width=80)
        self.treeview.column("cards", width=130)
        self.treeview.column("sum", width=60)
        self.treeview.grid(row=0, column=0, sticky="news")

        # Adding a vertical scrollbar to the self.treeview
        self.scrollbar_y = tb.Scrollbar(self.frame_count, orient="vertical", command=self.treeview.yview)
        self.scrollbar_y.grid(row=0, column=1, sticky="ns")
        self.treeview.configure(yscrollcommand=self.scrollbar_y.set)

        # Start and Stop buttons
        self.start_button = tb.Button(self.frame_count, text="Start Bet", command=self.start_bet)
        self.start_button.grid(pady=10, column=0, row=1, sticky="news")

        self.stop_button = tb.Button(self.frame_count, text="Stop Bet", command=self.stop_bets, bootstyle="danger")
        self.stop_button.grid(pady=10, column=0, row=1, sticky="news")
        self.stop_button.grid_remove()  # Initially hidden

        # Left and right frames within rl_frame for status and controls
        self.rl_frame = tb.Frame(self.frame_count)
        self.rl_frame.grid(row=2, column=0, sticky=W, columnspan=2)

        self.left_frame = tb.Frame(self.rl_frame)
        self.left_frame.grid(row=2, column=0, sticky="nw")

        # Add labels for status, running count, true count, etc.
        self.status_label = tb.Label(self.left_frame, text="Status: Processing", anchor=W, padding=5, width=20)
        self.status_label.grid(row=0, column=0, sticky=W)

        self.game_count_label = tb.Label(self.left_frame, text="Game count: 0", anchor=W, padding=5)
        self.game_count_label.grid(row=1, column=0, sticky=W)

        self.true_count_label = tb.Label(self.left_frame, text="True Count: 0", anchor=W, padding=5)
        self.true_count_label.grid(row=2, column=0, sticky=W)

        self.total_card_count = tb.Label(self.left_frame, text="Total Cards: 0", anchor=W, padding=5)
        self.total_card_count.grid(row=3, column=0, sticky=W)

        self.remaining_card_label = tb.Label(self.left_frame, text="Remaining Cards: 0", anchor=W, padding=5)
        self.remaining_card_label.grid(row=4, column=0, sticky=W)

        self.total_loss = tb.Label(self.left_frame, text="Total loss: 0", anchor=W, padding=5)
        self.total_loss.grid(row=5, column=0, sticky=W)

        # Right frame for change room and bets
        right_frame = tb.Frame(self.rl_frame)
        right_frame.grid(row=2, column=1, sticky="nw")

        self.stop_game_label = tb.Label(right_frame, text="Stop Until:", anchor=W, padding=5)
        self.stop_game_label.grid(row=0, column=0, sticky=W, padx=5)
        
        self.stop_game_cbox = tb.Combobox(right_frame, width=7, values=["50", "100", "200", "300", "500"])
        self.stop_game_cbox.grid(row=1, column=0, sticky=W, padx=10)
        self.stop_game_cbox.set("50")

        self.lost_stop_label = tb.Label(right_frame, text="Move Until:", anchor=W, padding=5)
        self.lost_stop_label.grid(row=2, column=0, sticky=W, padx=5)

        lost_range = list(range(1, 10))
        self.loss_stop_cbox = tb.Combobox(right_frame, values=lost_range, width=7)
        self.loss_stop_cbox.grid(row=3, column=0, sticky=W, padx=10)
        self.loss_stop_cbox.set(3)

        self.arduino = ArduinoPort(root)
        self.loss_count = 0
        self.game_count = 0

    def check_status_area(self, region, template, method=cv2.TM_SQDIFF_NORMED, threshold=0.1):
        """Check for the presence of a template in a given screen region."""
        x, y, w, h = region  # Assuming region is a tuple (x, y, width, height)
        screenshot = pyautogui.screenshot(region=(x, y, w, h))
        img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Template matching
        result = cv2.matchTemplate(gray_img, template, method)
        min_val, _, min_loc, _ = cv2.minMaxLoc(result)
        
        return min_val < threshold
    
    # def check_status_e(self, region, template, method=cv2.TM_CCOEFF_NORMED, threshold=0.6):
    #     """Check for the presence of a template in a given screen region using TM_CCOEFF_NORMED."""
    #     x, y, w, h = region  # Assuming region is a tuple (x, y, width, height)
        
    #     # Using mss for more accurate screenshots
    #     with mss.mss() as sct:
    #         # Define the region to capture
    #         monitor = {"top": y, "left": x, "width": w, "height": h}
    #         screenshot = sct.grab(monitor)
        
    #     # Convert to numpy array and process
    #     img = np.array(screenshot)
    #     gray_img = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)  # BGRA to Grayscale
        
    #     # Template matching
    #     result = cv2.matchTemplate(gray_img, template, method)
    #     min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        
    #     # Return True if the match value is above the threshold (for CCOEFF methods, higher is better)
    #     return max_val > threshold

    def check_start(self):
        return self.check_status_area(self.status_region['Start'], self.status_templates['Start'])
    
    def check_blackjack(self):
        return self.check_status_area(self.status_region['Blackjack'], self.status_templates['Blackjack'])
    
    # def check_win(self):
    #     return self.check_status_e(self.status_region['Win E'], self.status_templates['Win'])
    
    # def check_loss(self):
    #     return self.check_status_e(self.status_region['Loss E'], self.status_templates['Loss'])
    
    # def check_tie(self):
    #     return self.check_status_e(self.status_region['Tie E'], self.status_templates['Tie'])
    
    # def check_bust(self):
    #     return self.check_status_e(self.status_region['Bust E'], self.status_templates['Bust'])
    
    # def martin_system(self):
    #     """Determine the real-time outcome based on Player E and dealer sums."""
    #     outcome = None
    #     if self.check_win():
    #         outcome = "Win"
    #     elif self.check_loss() or self.check_bust():
    #         outcome = "Loss"
    #     elif self.check_tie():
    #         outcome = "Tie"
    #     return outcome
    
    def check_status(self, status_label):
        """Update the status label based on the game state."""
        try:
            stop_game = int(self.stop_game_cbox.get())  # Attempt to convert the value to an integer
        except ValueError:
            stop_game = 0  # Default value if conversion fails or no value is selected

        outcome_text = self.outcome_labels["Player E"].cget("text")
        loss_stop = int(self.loss_stop_cbox.get())

        if self.check_start():
            if not self.data_saved:
                # Break out if stop_game equals game_count
                if stop_game == self.game_count:
                    ards.send_command('stop')
                    self.stop_betting = True  # Set the flag to stop betting
                    self.start_button.grid()  # Show the start button again
                    self.stop_button.grid_remove()  # Hide stop button
                    return  # Exit function immediately, no further code will run

                if outcome_text == "Win":
                    self.game_count += 1
                    if not self.command_send:  # Ensure change_table is sent only once
                        ards.send_command('change_table')
                        self.command_send = True  # Set flag after sending the command
                        status_label.config(text="Status: Table Changing")
                        time.sleep(2)  # This can also be changed to after() for non-blocking behavior
                        self.loss_count = 0
                elif outcome_text == "Loss":
                    self.game_count += 1
                    if self.loss_count == loss_stop:
                        if not self.command_send:  # Ensure change_table is sent only once
                            ards.send_command('change_table')
                            self.command_send = True  # Set flag after sending the command
                            status_label.config(text="Status: Table Changing")
                            print("Loss stop activated!")
                            time.sleep(2)  # Again, could use after() if needed
                            self.loss_count = 0
                    if not self.command_send:  # Ensure change_table is sent only once
                        status_label.config(text="Status: 2x Bet")
                        ards.send_command('times_two')
                        self.save_all_data(self.labels, self.sum_labels)  # Assume save_all_data is defined elsewhere
                        self.data_saved = True  # Mark data as saved
                        self.command_send = True
                        self.loss_count += 1  # Increment loss counter
                        print(f"Player Lost Count: {self.loss_count}")
                        time.sleep(2)
                else:
                    self.game_count += 1
                    self.save_all_data(self.labels, self.sum_labels)  # Assume save_all_data is defined elsewhere
                    self.data_saved = True  # Mark data as saved
                    status_label.config(text="Status: Betting Started!")
                    ards.send_command('startbet')  

                # Update game and loss information in the UI
                self.total_loss.config(text=f"Total loss: {self.loss_count}")
                self.outcome_labels["Player E"].config(text="None")
                self.game_count_label.config(text=f"Game count: {self.game_count}")
                # Reset card labels and sums for all players
                for region_name in self.labels:
                    self.labels[region_name].config(text="No card detected")
                    self.sum_labels[region_name].config(text="Sum: 0")
        else:
            # Check for active players and update the status accordingly
            active_player_detected = False
            for player in ['A', 'B', 'C', 'D', 'E']:
                if self.check_status_area(self.status_region[f'Arrow {player}'], self.status_templates['Arrow']):
                    status_label.config(text=f"Status: Player {player} Active")
                    active_player_detected = True
                    break  # Stop checking once an active player is found

            if not active_player_detected:
                # If no specific player status is detected, set status to "Processing"
                status_label.config(text="Status: Processing")

            # Reset the flags when the game status is not "Start"
            self.data_saved = False
            self.command_send = False


    def count_cards_in_treeview(self, treeview):
        """Count the number of cards in the Treeview, treating each card as having a value of 1."""
        card_count = 0
        for item in treeview.get_children():
            row_data = treeview.item(item, 'values')  # Get the values for each row
            cards = row_data[1]  # Assuming the cards are in the second column (index 1)

            # Split the cards in case there are multiple cards in a single cell (e.g., "2H, 3S")
            card_list = cards.split(', ')
            card_count += len(card_list)  # Increment count by the number of cards in the list

        return card_count
    
    def check_reset_area(self, region, template, method=cv2.TM_CCOEFF_NORMED, threshold=0.97):
        """Check for the presence of a template in a given screen region."""
        gray_img = self.capture_region(region)

        # Template matching
        result = cv2.matchTemplate(gray_img, template, method)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        
        return max_val >= threshold, max_loc
    
    def count_remaining_cards(self, found_cards):
        remaining_cards = 312
        """Count the total number of cards detected."""
        # Check the presence of the 'Reset' template in the 'Reset' region
        region_name = 'Reset'
        region = self.status_region[region_name]
        template_name = 'Reset'
        template = self.status_templates[template_name]
        found, loc = self.check_reset_area(region, template)
        
        if found:
            found_cards[region_name] = [template_name]
            db.delete_all_data()
            db.populate_treeview(self.treeview)
            
        return remaining_cards
    
    def save_all_data(self, labels, sum_labels):
        """Save all data from the GUI labels to the database."""
        for region_name, label in labels.items():
            label_title_text = label.cget("text")
            sum_label_text = sum_labels[region_name].cget("text")
            
            # More robust extraction of the numeric part after "Sum: "
            sum_value = sum_label_text.split("Sum: ")[-1].strip() if "Sum: " in sum_label_text else "0"
            
            # Convert sum_value to float and handle possible conversion errors
            try:
                sum_value = float(sum_value)
            except ValueError:
                sum_value = 0  # Default to 0 if there's a conversion error

            # Ensure database interactions are wrapped in try-except for robustness
            try:
                # Assuming db.save_card_data and db.populate_treeview are thread-safe or called correctly
                db.save_card_data(region_name=region_name, label_value=label_title_text, sum_value=sum_value)
                db.populate_treeview(self.treeview)  # This might need to be outside the loop
            except Exception as e:
                print(f"Failed to save data for {region_name}: {e}")

        print("All data saved successfully.")

    def update_display(self, found_cards):
        """Update the display with detected card values and sums."""

        for region_name in self.labels.keys():
            if region_name in found_cards:
                cards = ", ".join(found_cards[region_name])
                self.labels[region_name].config(text=cards)

                total_sum = self.sum_cards(region_name, found_cards)
                self.sum_labels[region_name].config(text=f"Sum: {total_sum}")

                # Show dealer's outcome first
                player_outcome = self.martin_system(found_cards)
                self.outcome_labels["Player E"].config(text=player_outcome)

        detected_card_count = self.count_remaining_cards(found_cards)
        card_count = self.count_cards_in_treeview(self.treeview)
        self.remaining_card_count = detected_card_count - card_count 
        self.remaining_card_label.config(text=f"Remaining Cards: {self.remaining_card_count}")
        self.total_card_count.config(text=f"Total Cards: {card_count}")
        total_decks = int(self.remaining_card_count / 52) if self.remaining_card_count > 0 else 1  # Avoid division by zero
        running_count = self.update_count_from_treeview(self.treeview)
        true_count = int(running_count / total_decks) if total_decks > 0 else 0
        self.true_count_label.config(text=f"True Count: {true_count}")
    
    def check_blackjack_cards(self):
        self.blackjack_detected = False
        blackjack_sum = 21

        if self.check_blackjack():
            self.sum_labels["Player E"].config(text=f"Sum: {blackjack_sum}")
            self.outcome_labels["Player E"].config(text="BlackJack")      
            self.blackjack_detected = True

    def main_loop(self):
        """Main loop for detecting cards and updating the display."""
        # Initial setup (if these only need to happen once)
        db.create_table()
        db.populate_treeview(self.treeview)

        while not self.stop_betting:  # Control the loop with the stop_betting flag
            # try:
            # Detect cards and update UI
            cards_detected = self.check_all_cards()
            self.update_display(cards_detected)
            self.check_status(self.status_label)
            self.check_blackjack_cards()

            # Delay to prevent high CPU usage, adjust as needed
            time.sleep(0.1)

            # except Exception as e:
            #     print(f"Error during loop execution: {e}")
            #     # Optionally, break or continue based on error severity
            #     continue  # or 'break' to exit the loop on error

        # Cleanup or finalize operations after the loop
        print("Stopping the betting session and cleaning up resources.")

    # Define placeholder methods for start_bet and stop_bets
    def start_bet(self):
        selected_port = self.arduino.com_entry.get().strip()

        if not selected_port:
            messagebox.showerror("Error", "Please select a COM port.")
            return
        else:
            """Start the betting session."""
            self.stop_betting = False  # Reset the flag to allow betting

            self.stop_button.grid()  # Show the stop button when bet starts
            self.start_button.grid_remove()  # Hide start button
            self.game_count = 0

            messagebox.showinfo("Info", "Game Started")
            ards.send_command('clickSlotde')

            # Start the detection thread if it's not already running
            if self.detection_thread is None or not self.detection_thread.is_alive():
                self.detection_thread = threading.Thread(target=self.main_loop)
                self.detection_thread.daemon = True  # Ensures the thread exits when the main program does
                self.detection_thread.start()

    def stop_bets(self):
        """Stop the betting session."""
        if messagebox.askokcancel("Warning", "Are you sure you want to stop?"):
            self.stop_betting = True  # Set the flag to stop betting

            self.start_button.grid()  # Show the start button again
            self.stop_button.grid_remove()  # Hide stop button

class ConsoleLog:
    def __init__(self, root, log_file=None):
        self.root = root
        formatted_now = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = log_file if log_file else f"logs/log{formatted_now}.txt"

        # Create the console frame
        console_frame = tb.LabelFrame(self.root, text="Console", padding=10)
        console_frame.grid(row=4, column=0, sticky="news", padx=10, pady=5)

        # Create a ScrolledText widget for the console log
        self.console = scrolledtext.ScrolledText(console_frame, wrap=tb.WORD, width=60, height=7, state='normal')
        self.console.grid(row=0, column=0, sticky="news", padx=5, pady=5)
        self.console.insert(tb.END, "Console Log Started...\n")
        self.console.see(tb.END)

    def write(self, message):
        if message.strip() and self.root:  # Avoid logging empty messages
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.console.insert(tb.END, f"[{current_time}] {message}\n")
            self.console.see(tb.END)  # Scroll to the end

    def flush(self):
        pass  # Needed for Python's file-like objects, especially when redirecting stdout

    def save_to_file(self):
        try:
            with open(self.log_file, "w") as file:
                file.write(self.console.get("1.0", tb.END))  # Get all text from the start to the end
            print("Success: Logs saved successfully!")
        except Exception as e:
            print(f"Error: Failed to save logs: {e}")

    def stop_logging(self):
        print("Logging stopped.")

    def resume_logging(self):
        print("Logging resumed.")

if __name__ == "__main__":
    # Create the ttkbootstrap-themed window
    root = tb.Window(themename="darkly")

    # Create an instance of ArduinoPort and pass the root window
    arduino = ArduinoPort(root)
    frame_config = tb.Frame(root)
    frame_config.grid(row=3, column=0, sticky="news")
    cards = CardsDetector(frame_config)
    counts = CardsCounting(frame_config)
    console_log = ConsoleLog(root)  # Create the logging system instance
    sys.stdout = console_log  # Redirect stdout to console_log
    sys.stderr = console_log  # Also capture any error messages

    # Start the Tkinter event loop
    root.mainloop()
