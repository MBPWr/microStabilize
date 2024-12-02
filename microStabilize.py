import PySimpleGUI as sg
import cv2
from imutils.video import FPS
import numpy as np
import subprocess
import ast
import os
import time
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide" #Hide welcome message when importing pygame
import pygame


def process_file_settings(window, window_frame):
    settings = {}
    with open('microStabilize_settings.txt', 'r') as file:
        for line in file:
            # Split the line at the first occurrence of '='
            if '=' in line:
                key, value = line.split('=', 1)
                # Strip whitespace characters from key and value
                key = key.strip()
                value = value.strip()
                settings[key] = value
    window['Laser X'].Update(settings['Laser_X'])
    window['Laser Y'].Update(settings['Laser_Y'])
    window['Brightness_slider'].Update(settings['Frame_brightness'])
    window['Contrast_slider'].Update(settings['Frame_contrast'])
    window_frame = ast.literal_eval(settings['Window_frame_size']) #convert to tuple

    return window_frame

def write_settings_to_file(settings, file_path):
    with open(file_path, 'w') as file:
        for key, value in settings.items():
            file.write(f"{key} = {value}\n")

def move_motor(motor, relative):
    motor.move_to(motor.position + relative)

### Start of definitions for piezo actuator ###
def move_motor_piezo(ser, motor, relative):
    t = time.perf_counter()
    if motor == 'motor_x' or motor == 'motor_y' or motor == 'motor_z':
        ser.flushInput()
        i=0
        ser.write((motor[-1] + "R?" + '\n\r').encode('utf-8'))
        w =  ser.read(15).decode('ascii')
        i = re.findall("\d+\.\d+", w)
        if len(i)==0:
            i = re.findall("\d+", w)
        try:
            piezo_target = float(i[0]) + float(relative)
        except Exception as e:
            piezo_target = 76
            print(f"Piezo value to large. Set to 76. {e}")
        if piezo_target < 0 or piezo_target > 75:
            pass
        else:
            ser.write((motor[-1]+'V' + str(piezo_target) + '\n\r').encode('utf-8'))
            ser.read(1).decode('ascii')

def initialize_motors_piezo(values):
    ser = serial.Serial()

    ser.baudrate = 115200
    ser.bytesize = serial.EIGHTBITS
    ser.parity = serial.PARITY_NONE
    ser.stopbits = serial.STOPBITS_ONE
    ser.xonxoff = False
    ser.timeout = 1
    ser.write_timeout = 1
    ser.setDTR(False)
    ser.setRTS(False)
    try:
        port = str("COM"+ str(int(values['COM port'])))
    except Exception as e:
        ser.port = "COM7"
        print(f"Error in connecting to COM port. Port set to COM7. {e}")
    ser.port = "COM7"

    ser.close()  # In case it wasn't closed properly last time
    ser.open()
    return ser
### End of definitions for piezo actuator ###



def initialize_motors(apt):
    motor_x = apt.Motor(27600840)
    motor_x.set_hardware_limit_switches(1, 1)
    motor_x.backlash_distance = 0
    motor_y = apt.Motor(27600837)
    motor_y.set_hardware_limit_switches(1, 1)
    motor_y.backlash_distance = 0
    motor_z = apt.Motor(27260851)
    motor_z.backlash_distance = 0
    return motor_x, motor_y, motor_z

def start_camera(cap, values, window_frame):
    ret, frame = cap.read()
    #frame = cv2.resize(frame, None, fx=0.8, fy=0.8, interpolation=cv2.INTER_AREA)
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    #frame = imutils.resize(frame, width=1800)
    try:
        frame = frame[window_frame[1]:int(window_frame[1]+window_frame[3]),window_frame[0]:int(window_frame[0]+window_frame[2])]
    except Exception as e:
        frame = frame[0:900,0:900]
        print(f"Error in frame size. {e}")
    return frame

def variance_of_laplacian(image):
	# compute the Laplacian of the image and then return the focus
	# measure, which is simply the variance of the Laplacian
	return cv2.Laplacian(image, cv2.CV_64F).var()


def controller(img, brightness=255,contrast=127):
	brightness = int((brightness - 0) * (255 - (-255)) / (510 - 0) + (-255))
	contrast = int((contrast - 0) * (127 - (-127)) / (254 - 0) + (-127))
	if brightness != 0:
		if brightness > 0:
			shadow = brightness
			max = 255
		else:
			shadow = 0
			max = 255 + brightness
		al_pha = (max - shadow) / 255
		ga_mma = shadow
		# The function addWeighted calculates
		# the weighted sum of two arrays
		cal = cv2.addWeighted(img, al_pha,img, 0, ga_mma)
	else:
		cal = img
	if contrast != 0:
		Alpha = float(131 * (contrast + 127)) / (127 * (131 - contrast))
		Gamma = 127 * (1 - Alpha)
		# The function addWeighted calculates
		# the weighted sum of two arrays
		cal = cv2.addWeighted(cal, Alpha,cal, 0, Gamma)
	return cal
    
#Function to track and sace ROI position for performance evaluation
def save_differences(x_diff, y_diff, filename):
    
    # Prepare the data to be written to the file
    data = f"{x_diff} {y_diff}\n"
    
    # Write the data to the file
    with open(filename, 'a') as file:
        file.write(data)

def cv2_to_bytes(cv2_image):
    """Convert a CV2 image to bytes for PySimpleGUI's Image element."""
    _, encoded_image = cv2.imencode('.png', cv2_image)
    return encoded_image.tobytes()

def layout_frame():
    return [sg.Frame(layout=[[sg.Button('Change frame', size=(14, 1))],
                             [sg.Button('Background', size=(10, 1)),sg.Button('✓', size=(2, 1), visible = False),  sg.Checkbox('', size=(2, 1), default=False, key="background_checkbox", visible = True),
                             sg.Combo(['-1', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11'], default_value='-1', key='colormap', visible = False)],
                             [sg.Button('Add laser X&Y', size =(14, 1)), sg.Checkbox(' ', default=False, key="Laser spot", visible = False)],
                             [sg.Slider(range=(1,640), orientation = 'h', key='Laser X', size=(12,10),default_value='320')],
                             [sg.Slider(range=(1,480), orientation = 'h', key='Laser Y', size=(12,10),default_value='240')],],
                             title='Frame', relief=sg.RELIEF_FLAT, border_width=1)]

def layout_actuators():
    return [sg.Frame(layout=[[sg.Button('↑', size=(6, 1)),sg.Button('ⓧ', size=(2, 1))],
                             [sg.Button('←', size=(2, 1)),sg.Button('→', size=(2, 1))],
                             [sg.Button('↓', size=(6, 1)),sg.Button('⨀', size=(2, 1))],
                             [sg.Slider(range=(1, 64), orientation='h', size=(9, 10),default_value='2', key='Kinesis_speed')],
                             [sg.Button('Init. motors', size=(10, 1))],
                             [sg.Button('Init. joystick', size=(10, 1))],
                             [sg.Button('Auto focus', size=(10, 1), visible = False)]], title='Actuators', relief=sg.RELIEF_FLAT, border_width=1)]

def layout_stabilize():
    return [sg.Frame(layout=[[sg.Button('Select ROI', size=(10, 1))],
                             [sg.Button('Track', size=(10, 1))],
                             [sg.Button('Stabilize', size=(10, 1)), sg.Checkbox('', default=False, key="stabilize_checkbox", visible = False )],
                             [sg.Text('Brightness:', size =(10, 1))],
                             [sg.Slider(range=(1, 255), orientation='h', size=(9, 10),default_value='255', key='Brightness_slider', disable_number_display = True)],
                             [sg.Text('Contrast:', size =(10, 1))],
                             [sg.Slider(range=(1, 255), orientation='h', size=(9, 10),default_value='127', key='Contrast_slider', disable_number_display = True)]],title='Stabilize',  relief=sg.RELIEF_FLAT, border_width=1)]


def main():
    #['File', ['New', 'Open', 'Save', 'Exit', ]]
    menu_def = [['Settings', ['Open', 'Save'], ],  ['Info', ['Joystick','Load image', 'About']], ]
    layout = [  [sg.Menu(menu_def),
                sg.Column([layout_frame()]),
                sg.Column([layout_stabilize()]),
                sg.Column([layout_actuators()])],
                [sg.Image(key="-IMAGE_DISPLAY-")]]
                #[sg.Button('Exit')]]

    # Create the Window
    window = sg.Window('MicroStabilize', layout, font=('Helvetica', 12))
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    ROI_selected = False
    Track_started = False
    Motors_initialized = False
    motor_moved = False
    Joystick_initialized = False
    settings_loaded = False
    background_captured = False
    hat = (0,0)
    Threshold = 0
    frames = 0
    window_frame = (0,0,900,900)
    while True:
        event, values = window.read(timeout = 0)
        try:
            frame = start_camera(cap, values, window_frame)
        except Exception as e:
            print(f"Error in starting camera. {e}")

        fps = FPS().start()
        if event == sg.WIN_CLOSED or event == 'Exit': # if user closes window or clicks cancel
            if Motors_initialized == True:
                apt.core._cleanup()
            break

        if not settings_loaded:
            window_frame = process_file_settings(window, window_frame)
            settings_loaded = True
        
        if event == 'Change frame':
            ret, frame = cap.read()
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            window_frame = cv2.selectROI("Select frame", frame, fromCenter=False, showCrosshair=True)
            window_frame = tuple(abs(x) for x in window_frame)
            cv2.destroyAllWindows()
            
        if event == 'Add laser X&Y':
            if not values['Laser spot']:
                window['Laser spot'].Update(value = True)
                window['Add laser X&Y'].Update(button_color=('Black', 'Green'))
            if values['Laser spot']:
                window['Laser spot'].Update(value = False)
                window['Add laser X&Y'].Update(button_color=('Black', 'Gray'))
            
        if event == 'Background':
            background = frame
            background_captured = True

        if event == 'Open':
            file_path = "microStabilize_settings.txt"
            subprocess.Popen(["notepad.exe", file_path])

        if event == 'Load image':
            try:
                # Ask the user to select an image file
                image_path = sg.popup_get_file("Select Image", file_types=(("Image Files", "*.png;*.jpg;*.jpeg;*.bmp"),))
                if image_path:
                    image = cv2.imread(image_path)
                    if image is not None:
                        # Convert the image to bytes for PySimpleGUI
                        image_bytes = cv2_to_bytes(image)
                        window["-IMAGE_DISPLAY-"].update(data=image_bytes)
                # Ask the user to select a template file
                template_path = sg.popup_get_file("Select Template", file_types=(("Image Files", "*.png;*.jpg;*.jpeg;*.bmp"),))
                if template_path:
                    template = cv2.imread(template_path)
                    if template is not None:
                        sg.popup("Template loaded successfully!")

                if image is not None and template is not None:
                    # Perform template matching
                    result = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
                    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

                    # Draw rectangle on the image at the match location
                    h, w, _ = template.shape
                    top_left = max_loc
                    bottom_right = (top_left[0] + w, top_left[1] + h)
                    image_with_rectangle = image.copy()
                    cv2.rectangle(image_with_rectangle, top_left, bottom_right, (0, 255, 0), 2)

                    # Update display with the result
                    image_bytes = cv2_to_bytes(image_with_rectangle)
                    window["-IMAGE_DISPLAY-"].update(data=image_bytes)
                    print("Template top_left corner location is: ", max_loc, "Confidence level is: " + str(int(round(max_val, 2)*100))+"%")
                else:
                    sg.popup("Please load both image and template before finding the template.")
            except Exception as e:
                print(f"Error. {e}")

            

        if event == 'Save':
            settings = {
                'Threshold': '0',
                'Window_frame_size': '(0,0,900,900)',
                'Frame_brightness': '255',
                'Frame_contrast': '127',
                'Laser_X': '11',
                'Laser_Y': '240',
                'Actuator_COM_port': 'COM7',
                'apt.Motor_x': '27600840',
                'apt.Motor_y': '27600837',
                'apt.Motor_z': '27260851'
            }

            settings['Laser_X'] = int(values['Laser X'])
            settings['Laser_Y'] = int(values['Laser Y'])
            settings['Frame_brightness'] = int(values['Brightness_slider'])
            settings['Frame_contrast'] = int(values['Contrast_slider'])
            settings['Window_frame_size'] = window_frame


            # Write the settings to the file
            write_settings_to_file(settings, 'microStabilize_settings.txt')

        if event == 'Joystick':
            buttons_mapping = "XBox One Controller Map:\n" + "D-Pad Up = Up\n" + "D-Pad Down = Down\n" + "D-Pad Left = Left\n" + "D-Pad Right = Right\n"
            buttons_mapping = buttons_mapping + "A = speed - 1\n" + "B = speed + 1\n" + "L1 = speed --\n" + "R1 = speed ++\n"
            sg.popup(buttons_mapping, title='XBox One Controller Map')
        if event == 'About':
            sg.popup("Software by Marek Burakowski, Wrocław University of Science and Technology, 2024", title='About')
            
            
        if event == 'Select ROI':
            initBB = cv2.selectROI("Select ROI", frame, fromCenter=False,
                                       showCrosshair=True)
            cropped_frame = frame[int(initBB[1]):int(initBB[1]+initBB[3]), int(initBB[0]):int(initBB[0]+initBB[2])]
            cv2.imwrite("Last_selected_region.jpg", cropped_frame)
            template = cv2.imread('Last_selected_region.jpg', 0)
            h, w = template.shape
            result = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            temp_location = location = max_loc
            old_location = [location[0],location[1]]
            ROI_selected = True
            window['Select ROI'].Update(button_color=('Black', 'Green'))
            cv2.destroyAllWindows()
            
        if event == 'Track' and Track_started:
            Track_started = False
            window['Track'].Update(button_color=('Black', 'Red'))
            event, values = window.read(timeout = 10)

        if event == 'Track' and not ROI_selected:
            print(f"ROI not selected")
            
        if event == 'Stabilize' and (not ROI_selected or not Track_started or not Motors_initialized):
            print(f"ROI not selected or Tracking not started or Motors not initialized")
            
        if (event == 'Track' and ROI_selected) or Track_started:
            result = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            location = max_loc
            if (abs(temp_location[0]-location[0]) > 20) or (abs(temp_location[1]-location[1]) > 20):
                loc = np.where( result >= 0.6)

                if isinstance(loc, (tuple, np.ndarray)):
                    for i in range(len(loc[0])):
                        if (abs(temp_location[0]-loc[0][i]) < 20) and (abs(temp_location[1]-loc[1][i]) < 20):
                            location = (loc[0][i], loc[1][i])

                        else:
                            location = temp_location
                else:
                    location = temp_location
            else:
                temp_location = location

            bottom_right = (location[0] + w, location[1] + h)
            cv2.rectangle(frame, location, bottom_right, 255, 1)  
            if max_val > 0.7:
                Track_started = True
                window['Track'].Update(button_color=('Black', 'Green'))
            if max_val <= 0.7:
                Track_started = False
                window['Track'].Update(button_color=('Black', 'Red'))

        if event == 'Init. joystick' and Joystick_initialized == False:
            pygame.init()
            pygame.joystick.init()
            joystick_count = pygame.joystick.get_count()
            if joystick_count == 0:
                print(f"No joystick connected.")
            else:
                joystick = pygame.joystick.Joystick(0)
                joystick.init()
                Joystick_initialized = True
                window['Init. joystick'].Update(button_color=('Black', 'Green'))

        if Joystick_initialized == True:
            pygame.event.pump()
            hat = joystick.get_hat(0)
            if joystick.get_button(4) == 1:
                window['Kinesis_speed'].update(kinesis_speed-3)
            if joystick.get_button(5) == 1:
                window['Kinesis_speed'].update(kinesis_speed+3)
            if joystick.get_button(0) == 1:
                window['Kinesis_speed'].update(kinesis_speed-1)
                time.sleep(0.1)
            if joystick.get_button(1) == 1:
                window['Kinesis_speed'].update(kinesis_speed+1)
                time.sleep(0.1)
                
            
            

        if event == 'Init. motors' and Motors_initialized == True:
            apt.core._cleanup()
            Motors_initialized == False
            window['Init. motors'].Update(button_color=('Black', 'Red'))
        if event == 'Init. motors' and Motors_initialized == False:
            try:
                import thorlabs_apt as apt
                motor_x, motor_y, motor_z = initialize_motors(apt)
                window['Init. motors'].Update(button_color=('Black', 'Green'))
                Motors_initialized = True
            except Exception as e:
                print(f"No motors found. {e}")

        if (event == 'Stabilize' or values['stabilize_checkbox']) and ROI_selected and Track_started:
            x_diff = old_location[0]-location[0]
            y_diff = old_location[1]-location[1]
            #save_differences(x_diff,y_diff,"differences.txt")

        if (event == 'Stabilize' or values['stabilize_checkbox']) and Motors_initialized and ROI_selected and Track_started:
            x_diff = old_location[0]-location[0]
            y_diff = old_location[1]-location[1]
            #save_differences(x_diff,y_diff,diff)
            if abs(x_diff) > Threshold or abs(y_diff) > Threshold :
                if  x_diff < Threshold:
                    move_motor(motor_x,+0.0001)
                    print("moved +x")
                if x_diff > Threshold:
                    move_motor(motor_x,-0.0001)
                    print("moved -x")
                if y_diff < Threshold:
                    move_motor(motor_y,-0.0001)
                    print("moved -y")
                if y_diff > Threshold:
                    move_motor(motor_y,+0.0001)
                    print("moved +y")
                #For piezo the parameters are: move_motor(ser,'motor_y',+1)
        try:            
            focus_value = variance_of_laplacian(frame)
        except Exception as e:
            print(f"Error in calculating focus value. {e}")
            
        try:
            kinesis_speed = int(values['Kinesis_speed'])
        except:
            print(f"Error in setting kinesis speed. {e}")

        if motor_moved:
            for key in ['←', '→', '↑', '↓', 'ⓧ', '⨀']:
                window[key].Update(button_color=('white', '#283B5B'))
            motor_moved = False
                    
        if (event == '←' or hat == (-1,0)) and Motors_initialized:
            move_motor(motor_x,-0.0002*kinesis_speed)
            window['←'].Update(button_color=('black', 'Green'))
            motor_moved = True
        if (event == '→' or hat == (1,0)) and Motors_initialized:
            move_motor(motor_x,0.0002*kinesis_speed)
            window['→'].Update(button_color=('black', 'Green'))
            motor_moved = True
        if (event == '↑' or hat == (0,1)) and Motors_initialized:
            move_motor(motor_y,0.0002*kinesis_speed)
            window['↑'].Update(button_color=('black', 'Green'))
            motor_moved = True
        if (event == '↓' or hat == (0,-1)) and Motors_initialized:
            move_motor(motor_y,-0.0002*kinesis_speed)
            window['↓'].Update(button_color=('black', 'Green'))
            motor_moved = True
        if event == 'ⓧ' and Motors_initialized:
            move_motor(motor_z,0.0015*kinesis_speed)
            window['ⓧ'].Update(button_color=('black', 'Green'))
            motor_moved = True
        if event == '⨀' and Motors_initialized:
            move_motor(motor_z,-0.0015*kinesis_speed)
            window['⨀'].Update(button_color=('black', 'Green'))
            motor_moved = True

        if event == 'Auto focus' and Motors_initialized:
            frame = start_camera(cap)
            cv2.imshow('Frame', frame)
            c = cv2.waitKey(1)
            focus = variance_of_laplacian(frame)
            move_motor(motor_z,0.002*2*(-10))
            time.sleep(0.1)
            frame = start_camera(cap)
            cv2.imshow('Frame', frame)
            c = cv2.waitKey(1)
            for i in range(-20,40,1):
                move_motor(motor_z,0.0015)
                time.sleep(0.01)
                frame = start_camera(cap)
                cv2.imshow('Frame', frame)
                c = cv2.waitKey(1)
                if variance_of_laplacian(frame) > focus:
                    focus = variance_of_laplacian(frame)
            for i in range(0,60,1):
                if variance_of_laplacian(frame) < focus*0.99:
                    move_motor(motor_z,-0.0015)
                    time.sleep(0.01)
                    frame = start_camera(cap)
                    cv2.imshow('Frame', frame)
                    c = cv2.waitKey(1)
                else:
                    break
                

        info = [
            ("Difference", "X:" + str(old_location[0]-location[0]) + "Y:" +str(old_location[1]-location[1]) if ROI_selected and Track_started else "-"),
            ("Confidence", (str(int(round(max_val, 2)*100))+"%") if Track_started else "0%"),
            ("Focus value", (str(int(round(focus_value, 2)*100))) if True else "0%"), 
            ("FPS", "{:.0f}".format(frames)),
        ]
        (H, W) = frame.shape[:2]
        try:
            for (i, (k, v)) in enumerate(info):
                text = "{}: {}".format(k, v)
                cv2.putText(frame, text, (10, H - ((i * 20) + 20)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
        except Exception as e:
            print(f"Error in adding info. {e}")
        if values['colormap'] != '-1':
            frame = cv2.applyColorMap(frame, int(values['colormap']))
            
     
        frame = controller(frame, values['Brightness_slider'],values['Contrast_slider'])
        if values["Laser spot"]:
            try:    
                cv2.circle(frame,(int(values["Laser X"]),int(values["Laser Y"])), 2, (255,255,255))
            except Exception as e:
                print(f"Error in laser spot. {e}")
        if values['background_checkbox'] and background_captured:
            cv2.imshow('Frame', frame-background)
        else:
            cv2.imshow('Frame', frame)
        
        fps.update()
        fps.stop()

        try:
            frames = fps.fps()
        except Exception as e:
            print(f"Error in FPS. {e}")
    cv2.destroyAllWindows()
    cap.release()
    window.close()

if __name__ == "__main__":
    main()
