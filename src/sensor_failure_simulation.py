Prototyp-Code:

import time
import random


# Sensorüberprüfung & Fehlererkennung


def prüfe_sensoren():
    """Simuliert die Sensorprüfung und erkennt einen möglichen Ausfall."""
    sensor_status = random.choice(["ok", "ok", "fehler"])  # Wahrscheinlichkeit für Ausfall ~33%
    return sensor_status


# Notfall-Übergabe Strategie


def notfall_übergabe():
    """Startet die Notfall-Übergabe an den Fahrer."""
    print("\n Notfall! Sensorausfall erkannt!")
    print(" Akustischer Alarm wird ausgelöst...")
    print(" Visuelle Warnung auf dem Display!")

    übernahmezeit = 30  # Zeit in Sekunden (simuliert)
    warnzeit = 0
    übergabe_erfolgreich = False

    while warnzeit < übernahmezeit:
        print(f" Warte auf Fahrerübernahme... ({warnzeit}/{übernahmezeit} Sekunden)")
        time.sleep(3)  # Warte 3 Sekunden pro Schritt (Simulation)
        warnzeit += 3
        
        # Simulieren, dass der Fahrer in 50% der Fälle reagiert
        if random.random() < 0.5:
            übergabe_erfolgreich = True
            break

    if übergabe_erfolgreich:
        print(" Fahrer hat übernommen! Fahrzeug unter manueller Kontrolle.")
    else:
        print(" Keine Reaktion vom Fahrer! Notfallmodus wird aktiviert.")
        notfall_stopp()

# Notfall-Strategie falls keine Reaktion


def notfall_stopp():
    """Falls der Fahrer nicht reagiert, führt das Fahrzeug ein sicheres Anhalten durch."""
    print(" Fahrzeug leitet sicheres Notfall-Anhalten ein...")
    print(" Notbremsung wird durchgeführt...")
    print(" Automatische Notrufsystem wird aktiviert!")


# Hauptsimulation


print(" Systemüberprüfung läuft...")
time.sleep(2)

sensor_status = prüfe_sensoren()

if sensor_status == "fehler":
    notfall_übergabe()
else:
    print(" Alle Sensoren funktionieren. Fahrt läuft normal.")
