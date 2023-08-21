from pynput import keyboard
import time

#help(keyboard.Key)
#exit()

def on_press(key):
    print("only the key: ", key)
    print("the name is: ", key.name)
    #if key == 'm':
    #    print("emme")

    try:
        if key == keyboard.Key.m:
            print("emmme")
    except:
        print("exxetto")

listener = keyboard.Listener(on_press=on_press)
listener.start()

while True:
    time.sleep(1)
    print("mimmo")
