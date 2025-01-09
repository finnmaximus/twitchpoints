import os
import sys
import requests
import time

def print_help():
    print("""
Comandos disponibles:
start         - Inicia el bot de Twitch
stop          - Detiene el bot
status        - Muestra el estado actual
list          - Muestra streams activos
log           - Muestra los últimos logs
help          - Muestra esta ayuda
    """)

def main():
    if len(sys.argv) < 2:
        print_help()
        return

    command = sys.argv[1]
    
    if command == "start":
        os.system("python main.py")
    elif command == "status":
        try:
            response = requests.get("http://localhost:8080/status")
            print(response.text)
        except:
            print("El bot no está en ejecución")
    elif command == "list":
        try:
            response = requests.get("http://localhost:8080/list")
            print(response.text)
        except:
            print("El bot no está en ejecución")
    elif command == "log":
        try:
            with open("twitch_watcher.log", "r") as f:
                print(f.read())
        except:
            print("No hay archivo de logs")
    else:
        print_help()

if __name__ == "__main__":
    main()
