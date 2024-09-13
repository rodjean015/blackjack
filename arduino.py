from tkinter import messagebox
import subprocess
import serial
import serial.tools.list_ports

# Function to send commands to Arduino
def send_command(command):
    command = command.lower().strip()
    
    if serialInst and serialInst.is_open:
        serialInst.write(command.encode('utf-8'))
        print(command)
    else:
        print(f"Simulating command: {command}")

# Function to compile Arduino sketch
def install_library(library_name):
    command = f'arduino-cli lib install {library_name}'
    try:
        output = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
        print(output.decode('utf-8'))
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error during library installation: {e.output.decode('utf-8')}")
        return False

def compile_sketch(sketch_path):
    command = f'arduino-cli compile --fqbn arduino:avr:leonardo {sketch_path}'  # Change to a compatible board
    try:
        output = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
        print(output.decode())
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error during compilation: {e.output.decode()}")
        return False

def upload_sketch(sketch_path, port):
    command = f'arduino-cli upload -p {port} --fqbn arduino:avr:leonardo {sketch_path}'  # Change to a compatible board
    try:
        output = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
        print(output.decode())
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error during upload: {e.output.decode()}")
        return False

def upload_code():
    sketch_path = 'arduino/blackjack/blackjack.ino'  
    port = serialInst.port if serialInst else None  # Check if serialInst is not None

    if port is None:
        print("Serial port not initialized.")
        messagebox.showerror("Error", "Serial port is not initialized. Please select a port.")
        return

    close_serial()  # Close the serial connection before uploading

    if install_library("Keyboard") and install_library("Mouse"):
        if compile_sketch(sketch_path):
            if upload_sketch(sketch_path, port):
                print("Code uploaded to Arduino.")
                messagebox.showinfo("Info", "Code uploaded to Arduino.")
            else:
                print("Failed to upload code. Please check the connection.")
                messagebox.showerror("Error", f"Failed to upload code to {port}. Please check the connection and try again.")
        else:
            print("Compilation failed. Please check the sketch.")
            messagebox.showerror("Error", "Compilation failed. Please check the sketch.")
    else:
        print("Failed to install library. Please check the connection.")
        messagebox.showerror("Error", "Failed to install library. Please check the connection.")
    
    init_serial(port)  # Reopen the serial connection after uploading

# Function to close serial connection
def close_serial():
    global serialInst
    if serialInst and serialInst.is_open:
        serialInst.close()
    print("Serial connection closed.")

# List available COM ports
def list_ports():
    ports = serial.tools.list_ports.comports()
    portsList = [port.device for port in sorted(ports)]
    return portsList

# Initialize serial communication
def init_serial(port):
    global serialInst
    serialInst = serial.Serial()
    serialInst.baudrate = 9600
    serialInst.port = port
    try:
        serialInst.open()
        print(f"Connected to {serialInst.portstr}.")
        return True
    except serial.SerialException as e:
        print(f"Serial connection error: {e}")
        return False
    

