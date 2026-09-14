import csv
import os
import random
import sys

# =============================================================================
# PARAMETER DEFINITION
# =============================================================================

# Ausgabepfad Parameter
USER_SPECIFIED_OUTPUT_BASE_PATH = ""  # Hier absoluten Pfad eintragen, z.B. "C:\\Users\\MyUser\\Simulations"
OUTPUT_DIRECTORY = "simulation_results"

# Sensor Fusion Parameter
SENSOR_FUSION_DELAY_S = 0.3  # Verzögerung der Wahrnehmungsdaten für Entscheidungen

# Fahrzeug Parameter
INITIAL_SPEED_KMH = 120
TARGET_SPEED_NORMAL_KMH = 90
TARGET_SPEED_DENSE_FOG_KMH = 60
TARGET_SPEED_EMERGENCY_STOP_KMH = 10

# Physik Parameter
DECELERATION_RATE_MPS2 = -2.5
PRECAUTIONARY_DECELERATION_RATE_MPS2 = -3.5
EMERGENCY_DECEL_MIN_MPS2 = -10.0
EMERGENCY_DECEL_MAX_MPS2 = -4.0
TIME_STEP_S = 0.1
MAX_SIMULATION_TIME_S = 300

# Wetter Parameter
DENSE_FOG_VISIBILITY_M = 50
MIN_PERCEPTION_RANGE_FOR_CONTINUATION_FOG_M = 20

# Sensor Parameter (Normal Bedingungen)
LONG_RANGE_LIDAR_NORMAL_M = 300
SHORT_RANGE_LIDAR_NORMAL_M = 50
CAMERA_NORMAL_M = 250

# Sensor Parameter (Dichter Nebel) - stark reduzierte, quellenbasierte Annahme
LIDAR_LR_EFFECTIVE_RANGE_DENSE_FOG_M = (30.0 , 50,0)  # stark reduzierte, quellenbasierte Annahme
LIDAR_SR_EFFECTIVE_RANGE_DENSE_FOG_M = 10  # stark reduzierte, quellenbasierte Annahme
CAMERA_FV_EFFECTIVE_RANGE_DENSE_FOG_M = 15  # stark reduzierte, quellenbasierte Annahme
CAMERA_FV_DETECTION_PROBABILITY_FOG = 0.4  # stark reduzierte, quellenbasierte Annahme

# Konvertierung km/h zu m/s
def kmh_to_mps(speed_kmh):
    return speed_kmh / 3.6

def mps_to_kmh(speed_mps):
    return speed_mps * 3.6

# =============================================================================
# SENSOR SIMULATION
# =============================================================================

def calculate_effective_perception_range(weather_condition):
    """Berechnet die effektive Wahrnehmungsreichweite basierend auf Sensoren und Wetter"""
    
    if weather_condition == "Normal":
        # Normale Bedingungen - beste verfügbare Reichweite
        ranges = [LONG_RANGE_LIDAR_NORMAL_M, SHORT_RANGE_LIDAR_NORMAL_M, CAMERA_NORMAL_M]
        return max(ranges), 1.0, LONG_RANGE_LIDAR_NORMAL_M, SHORT_RANGE_LIDAR_NORMAL_M, CAMERA_NORMAL_M
    
    elif weather_condition == "DenseFog":
        # Dichter Nebel - drastisch reduzierte Reichweiten
        
        # Objektreflektivität beeinflusst alle Sensoren
        object_reflectivity = random.uniform(0.1, 1.0)
        
        # Long-Range LiDAR mit Reflektivitätseinfluss
        lidar_base_range = random.uniform(30.0, 50.0)
        lidar_long_range = lidar_base_range * object_reflectivity
        
        # Kurzstrecken-LiDAR mit Reflektivitätseinfluss
        lidar_short_range = LIDAR_SR_EFFECTIVE_RANGE_DENSE_FOG_M * object_reflectivity
        
        # Kamera mit reduzierter Erkennungswahrscheinlichkeit und Reflektivitätseinfluss
        camera_range = CAMERA_FV_EFFECTIVE_RANGE_DENSE_FOG_M * object_reflectivity
        camera_effective = camera_range if random.random() < CAMERA_FV_DETECTION_PROBABILITY_FOG else 0
        
        ranges = [lidar_long_range, lidar_short_range, camera_effective]
        return max(ranges), object_reflectivity, lidar_long_range, lidar_short_range, camera_effective
    
    return 0, 1.0, 0, 0, 0

def get_delayed_perception_range(perception_history, current_time, active_sensor_fusion_delay):
    """Gibt die verzögerte Wahrnehmungsreichweite basierend auf der Historie zurück"""
    delay_time = current_time - active_sensor_fusion_delay
    
    # Finde den nächstliegenden Zeitpunkt in der Historie
    if not perception_history:
        return 0
    
    # Suche nach dem passenden Zeitpunkt oder dem nächstliegenden
    for time_stamp, perception_range in reversed(perception_history):
        if time_stamp <= delay_time:
            return perception_range
    
    # Falls kein passender Zeitpunkt gefunden, verwende den ältesten verfügbaren
    return perception_history[0][1]

# =============================================================================
# SIMULATION LOGIC
# =============================================================================

def run_simulation(weather_condition):
    """Führt die Simulation für eine Wetterbedingung durch"""
    
    print(f"\n=== Simulation Start: {weather_condition} ===")
    
    # Initialisierung
    current_speed_mps = kmh_to_mps(INITIAL_SPEED_KMH)
    target_speed_mps = kmh_to_mps(TARGET_SPEED_NORMAL_KMH if weather_condition == "Normal" else TARGET_SPEED_DENSE_FOG_KMH)
    emergency_stop_speed_mps = kmh_to_mps(TARGET_SPEED_EMERGENCY_STOP_KMH)
    
    # Dynamische Sensor Fusion Verzögerung basierend auf Wetterbedingungen
    active_sensor_fusion_delay = 0.5 if weather_condition == "DenseFog" else SENSOR_FUSION_DELAY_S
    
    distance_total_m = 0
    time_s = 0
    deceleration_active = False
    emergency_stop_active = False
    emergency_decel_rate = 0
    
    # Wahrnehmungshistorie für Sensor Fusion Delay
    perception_history = []
    
    # Datensammlung
    simulation_data = []
    events_log = []
    
    # Startereignis
    events_log.append(f"Simulation Start - Wetter: {weather_condition}, Anfangsgeschwindigkeit: {INITIAL_SPEED_KMH} km/h")
    
    # Radarausfall sofort erkannt
    events_log.append(f"Zeit {time_s:.1f}s: Radarausfall erkannt - Verzögerung eingeleitet")
    deceleration_active = True
    
    while time_s < MAX_SIMULATION_TIME_S:
        # Aktuelle Wahrnehmungsreichweite und Objektreflektivität berechnen
        current_perception_range, object_reflectivity, lidar_lr_range, lidar_sr_range, camera_effective_range = calculate_effective_perception_range(weather_condition)
        
        # Wahrnehmungshistorie aktualisieren
        perception_history.append((time_s, current_perception_range))
        
        # Alte Einträge aus der Historie entfernen (älter als Delay + Puffer)
        cutoff_time = time_s - (active_sensor_fusion_delay + 1.0)
        perception_history = [(t, p) for t, p in perception_history if t >= cutoff_time]
        
        # Verzögerte Wahrnehmungsreichweite für Entscheidungen verwenden
        delayed_perception_range = get_delayed_perception_range(perception_history, time_s, active_sensor_fusion_delay)
        
        # Lane Keeping Erfolg basierend auf verzögerter Wahrnehmungsreichweite
        lane_keeping_success = delayed_perception_range > 15.0
        
        # Entscheidungslogik für Notbremsung bei dichtem Nebel (mit verzögerter Wahrnehmung)
        if weather_condition == "DenseFog" and not emergency_stop_active:
            # Wahrnehmungsqualität als zusätzlicher Faktor
            perception_quality = random.uniform(0.1, 0.9)
            
            if delayed_perception_range < MIN_PERCEPTION_RANGE_FOR_CONTINUATION_FOG_M or perception_quality < 0.3:
                target_speed_mps = emergency_stop_speed_mps
                emergency_stop_active = True
                
                # Grund für Notbremsung im Log vermerken
                reason = "Wahrnehmungsreichweite" if delayed_perception_range < MIN_PERCEPTION_RANGE_FOR_CONTINUATION_FOG_M else "Wahrnehmungsqualität"
                events_log.append(f"Zeit {time_s:.1f}s: Notbremsung aktiviert - Grund: {reason} (Reichweite: {delayed_perception_range:.1f}m, Qualität: {perception_quality:.2f})")
        
        # Mehrstufige Verzögerungslogik
        if emergency_stop_active:
            if emergency_decel_rate == 0:
                emergency_decel_rate = random.uniform(EMERGENCY_DECEL_MIN_MPS2, EMERGENCY_DECEL_MAX_MPS2)
                events_log.append(f"Zeit {time_s:.1f}s: Emergency braking rate of {emergency_decel_rate:.2f} m/s^2 selected.")
            active_deceleration = emergency_decel_rate
        elif weather_condition == "DenseFog":
            active_deceleration = PRECAUTIONARY_DECELERATION_RATE_MPS2
        else:
            active_deceleration = DECELERATION_RATE_MPS2
        
        # Geschwindigkeit vor dem Update speichern für Distanzberechnung
        speed_before_step = current_speed_mps
        
        # Geschwindigkeitsupdate
        if deceleration_active and current_speed_mps > target_speed_mps:
            current_speed_mps += active_deceleration * TIME_STEP_S
            if current_speed_mps < target_speed_mps:
                current_speed_mps = target_speed_mps
                events_log.append(f"Zeit {time_s:.1f}s: Zielgeschwindigkeit {mps_to_kmh(target_speed_mps):.1f} km/h erreicht")
        
        # Distanzupdate mit durchschnittlicher Geschwindigkeit
        average_speed = (speed_before_step + current_speed_mps) / 2
        distance_total_m += average_speed * TIME_STEP_S
        
        # Daten sammeln (aktuelle Wahrnehmungsreichweite für Ausgabe)
        simulation_data.append({
            'time': time_s,
            'speed_kmh': mps_to_kmh(current_speed_mps),
            'distance_total_m': distance_total_m,
            'effective_perception_range_m': current_perception_range,
            'deceleration_active': deceleration_active,
            'emergency_stop_active_fog': emergency_stop_active,
            'lane_keeping_success': lane_keeping_success,
            'object_reflectivity': object_reflectivity,
            'active_deceleration_mps2': active_deceleration,
            'lidar_lr_range_m': lidar_lr_range,
            'lidar_sr_range_m': lidar_sr_range,
            'camera_effective_range_m': camera_effective_range
        })
        
        # Abbruchbedingung
        if current_speed_mps <= target_speed_mps and deceleration_active:
            events_log.append(f"Zeit {time_s:.1f}s: Simulation beendet - Zielgeschwindigkeit erreicht")
            break
        
        time_s += TIME_STEP_S
    
    # Finale Werte
    final_speed_kmh = mps_to_kmh(current_speed_mps)
    events_log.append(f"Simulation Ende - Endgeschwindigkeit: {final_speed_kmh:.1f} km/h, Gesamtstrecke: {distance_total_m:.1f}m, Gesamtzeit: {time_s:.1f}s")
    
    return simulation_data, events_log

# =============================================================================
# OUTPUT GENERATION
# =============================================================================

def create_output_directory():
    """Erstellt das Ausgabeverzeichnis mit Berücksichtigung des benutzerdefinierten Basispfads"""
    try:
        # Bestimme den vollständigen Ausgabepfad
        if USER_SPECIFIED_OUTPUT_BASE_PATH and os.path.exists(USER_SPECIFIED_OUTPUT_BASE_PATH):
            # Benutze den angegebenen Basispfad
            full_output_path = os.path.join(USER_SPECIFIED_OUTPUT_BASE_PATH, OUTPUT_DIRECTORY)
        else:
            # Fallback: Benutze das aktuelle Arbeitsverzeichnis
            if USER_SPECIFIED_OUTPUT_BASE_PATH and not os.path.exists(USER_SPECIFIED_OUTPUT_BASE_PATH):
                print(f"WARNUNG: Der angegebene Basispfad '{USER_SPECIFIED_OUTPUT_BASE_PATH}' existiert nicht.")
                print(f"Verwende stattdessen das aktuelle Arbeitsverzeichnis.")
            full_output_path = os.path.join(os.getcwd(), OUTPUT_DIRECTORY)
        
        # Erstelle das Verzeichnis, wenn es nicht existiert
        if not os.path.exists(full_output_path):
            os.makedirs(full_output_path)
        
        return full_output_path
    
    except Exception as e:
        # Bei Fehler: Fallback zum aktuellen Arbeitsverzeichnis
        print(f"FEHLER beim Erstellen des Ausgabeverzeichnisses: {str(e)}")
        print(f"Verwende stattdessen das aktuelle Arbeitsverzeichnis.")
        
        fallback_path = os.path.join(os.getcwd(), OUTPUT_DIRECTORY)
        if not os.path.exists(fallback_path):
            os.makedirs(fallback_path)
        
        return fallback_path

def save_csv_data(weather_condition, simulation_data):
    """Speichert CSV-Daten mit deutscher Formatierung"""
    output_path = create_output_directory()
    filename = os.path.join(output_path, f"sim_data_L5_radarausfall_{weather_condition}.csv")
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile, delimiter=';')
        
        # Header
        writer.writerow(['Time(s)', 'Speed(km/h)', 'Distance_Total(m)', 'EffectivePerceptionRange(m)', 
                         'DecelerationActive', 'EmergencyStopActive_Fog', 'LaneKeepingSuccess', 'ObjectReflectivity', 
                         'ActiveDecel(m/s^2)', 'LidarLRRange(m)', 'LidarSRRange(m)', 'CameraEffectiveRange(m)'])
        
        # Daten mit deutscher Formatierung (Komma als Dezimaltrennzeichen)
        for row in simulation_data:
            formatted_row = [
                str(round(row['time'], 2)).replace('.', ','),
                str(round(row['speed_kmh'], 2)).replace('.', ','),
                str(round(row['distance_total_m'], 2)).replace('.', ','),
                str(round(row['effective_perception_range_m'], 2)).replace('.', ','),
                str(row['deceleration_active']),
                str(row['emergency_stop_active_fog']),
                str(row['lane_keeping_success']),
                str(round(row['object_reflectivity'], 2)).replace('.', ','),
                str(round(row['active_deceleration_mps2'], 2)).replace('.', ','),
                str(round(row['lidar_lr_range_m'], 2)).replace('.', ','),
                str(round(row['lidar_sr_range_m'], 2)).replace('.', ','),
                str(round(row['camera_effective_range_m'], 2)).replace('.', ',')
            ]
            writer.writerow(formatted_row)
    
    print(f"CSV-Datei gespeichert: {filename}")

def save_report(weather_condition, events_log, simulation_data):
    """Speichert Textbericht"""
    output_path = create_output_directory()
    filename = os.path.join(output_path, f"sim_report_L5_radarausfall_{weather_condition}.txt")
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"=== L5 Autonomes Fahrzeug Simulation - Radarausfall ===\n")
        f.write(f"Wetterbedingung: {weather_condition}\n")
        f.write(f"Datum: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("=== Simulationsparameter ===\n")
        f.write(f"Anfangsgeschwindigkeit: {INITIAL_SPEED_KMH} km/h\n")
        f.write(f"Zielgeschwindigkeit Normal: {TARGET_SPEED_NORMAL_KMH} km/h\n")
        f.write(f"Zielgeschwindigkeit Dichter Nebel: {TARGET_SPEED_DENSE_FOG_KMH} km/h\n")
        f.write(f"Notbremsgeschwindigkeit: {TARGET_SPEED_EMERGENCY_STOP_KMH} km/h\n")
        f.write(f"Normale Verzögerungsrate: {DECELERATION_RATE_MPS2} m/s²\n")
        f.write(f"Vorsichtige Verzögerungsrate: {PRECAUTIONARY_DECELERATION_RATE_MPS2} m/s²\n")
        f.write(f"Notbremsung Verzögerungsbereich: {EMERGENCY_DECEL_MIN_MPS2} bis {EMERGENCY_DECEL_MAX_MPS2} m/s²\n")
        f.write(f"Zeitschritt: {TIME_STEP_S} s\n")
        f.write(f"Sensor Fusion Verzögerung: {SENSOR_FUSION_DELAY_S} s\n")
        f.write(f"Aktive Sensor Fusion Verzögerung: {0.5 if weather_condition == 'DenseFog' else SENSOR_FUSION_DELAY_S} s\n\n")
        
        # Wetterbedingte Sensorparameter hinzufügen
        f.write(f"=== Sensorparameter für {weather_condition} ===\n")
        if weather_condition == "Normal":
            f.write(f"Long-Range LiDAR Reichweite: {LONG_RANGE_LIDAR_NORMAL_M} m\n")
            f.write(f"Short-Range LiDAR Reichweite: {SHORT_RANGE_LIDAR_NORMAL_M} m\n")
            f.write(f"Kamera Reichweite: {CAMERA_NORMAL_M} m\n")
        elif weather_condition == "DenseFog":
            f.write(f"Long-Range LiDAR Reichweite (Nebel): 30.0-50.0 m (zufällig)\n")
            f.write(f"Short-Range LiDAR Reichweite (Nebel): bis zu {LIDAR_SR_EFFECTIVE_RANGE_DENSE_FOG_M} m (reflektivitätsabhängig)\n")
            f.write(f"Kamera Reichweite (Nebel): bis zu {CAMERA_FV_EFFECTIVE_RANGE_DENSE_FOG_M} m (reflektivitätsabhängig)\n")
            f.write(f"Kamera Erkennungswahrscheinlichkeit (Nebel): {CAMERA_FV_DETECTION_PROBABILITY_FOG}\n")
        f.write("\n")
        
        f.write("=== Ereignisprotokoll ===\n")
        for event in events_log:
            f.write(f"{event}\n")
        
        # Erweiterte Analyse für beide Wetterbedingungen
        f.write("\n=== Analyse ===\n")
        min_perception_range_achieved = min(d['effective_perception_range_m'] for d in simulation_data if 'effective_perception_range_m' in d)
        f.write(f"Minimale erreichte Wahrnehmungsreichweite: {min_perception_range_achieved:.1f} m\n")
        
        # Berechnung der durchschnittlichen Lane-Keeping-Erfolgsrate
        successful_lane_keeping_count = sum(1 for d in simulation_data if d.get('lane_keeping_success', False))
        total_data_points = len(simulation_data) if simulation_data else 1  # Vermeidung von Division durch Null
        lane_keeping_success_rate = (successful_lane_keeping_count / total_data_points) * 100 if simulation_data else 0.0
        f.write(f"Durchschnittliche Lane-Keeping-Erfolgsrate: {lane_keeping_success_rate:.1f}%\n")
        
        # Reflektivitätsbasierte Analyse für DenseFog
        if weather_condition == "DenseFog":
            f.write("\nDurchschnittliche Wahrnehmungsreichweite nach Reflektivität:\n")
            
            # Kategorisierung der Daten nach Reflektivität
            low_reflectivity_data = [d for d in simulation_data if d.get('object_reflectivity', 0) < 0.3]
            medium_reflectivity_data = [d for d in simulation_data if 0.3 <= d.get('object_reflectivity', 0) <= 0.7]
            high_reflectivity_data = [d for d in simulation_data if d.get('object_reflectivity', 0) > 0.7]
            
            # Berechnung der durchschnittlichen Wahrnehmungsreichweite für jede Kategorie
            if low_reflectivity_data:
                avg_low = sum(d['effective_perception_range_m'] for d in low_reflectivity_data) / len(low_reflectivity_data)
                f.write(f"Niedrige Reflektivität (<0.3): {avg_low:.1f} m\n")
            else:
                f.write(f"Niedrige Reflektivität (<0.3): N/A\n")
            
            if medium_reflectivity_data:
                avg_medium = sum(d['effective_perception_range_m'] for d in medium_reflectivity_data) / len(medium_reflectivity_data)
                f.write(f"Mittlere Reflektivität (0.3-0.7): {avg_medium:.1f} m\n")
            else:
                f.write(f"Mittlere Reflektivität (0.3-0.7): N/A\n")
            
            if high_reflectivity_data:
                avg_high = sum(d['effective_perception_range_m'] for d in high_reflectivity_data) / len(high_reflectivity_data)
                f.write(f"Hohe Reflektivität (>0.7): {avg_high:.1f} m\n")
            else:
                f.write(f"Hohe Reflektivität (>0.7): N/A\n")
            
            # Detaillierte Sensoranalyse nach Reflektivität
            f.write("\nDetaillierte Sensorleistung nach Reflektivität:\n")
            
            # Long-Range LiDAR
            f.write("Long-Range LiDAR:\n")
            if low_reflectivity_data:
                avg_lr_low = sum(d['lidar_lr_range_m'] for d in low_reflectivity_data) / len(low_reflectivity_data)
                f.write(f"  Niedrige Reflektivität (<0.3): {avg_lr_low:.1f} m\n")
            else:
                f.write(f"  Niedrige Reflektivität (<0.3): N/A\n")
            
            if medium_reflectivity_data:
                avg_lr_medium = sum(d['lidar_lr_range_m'] for d in medium_reflectivity_data) / len(medium_reflectivity_data)
                f.write(f"  Mittlere Reflektivität (0.3-0.7): {avg_lr_medium:.1f} m\n")
            else:
                f.write(f"  Mittlere Reflektivität (0.3-0.7): N/A\n")
            
            if high_reflectivity_data:
                avg_lr_high = sum(d['lidar_lr_range_m'] for d in high_reflectivity_data) / len(high_reflectivity_data)
                f.write(f"  Hohe Reflektivität (>0.7): {avg_lr_high:.1f} m\n")
            else:
                f.write(f"  Hohe Reflektivität (>0.7): N/A\n")
            
            # Short-Range LiDAR
            f.write("Short-Range LiDAR:\n")
            if low_reflectivity_data:
                avg_sr_low = sum(d['lidar_sr_range_m'] for d in low_reflectivity_data) / len(low_reflectivity_data)
                f.write(f"  Niedrige Reflektivität (<0.3): {avg_sr_low:.1f} m\n")
            else:
                f.write(f"  Niedrige Reflektivität (<0.3): N/A\n")
            
            if medium_reflectivity_data:
                avg_sr_medium = sum(d['lidar_sr_range_m'] for d in medium_reflectivity_data) / len(medium_reflectivity_data)
                f.write(f"  Mittlere Reflektivität (0.3-0.7): {avg_sr_medium:.1f} m\n")
            else:
                f.write(f"  Mittlere Reflektivität (0.3-0.7): N/A\n")
            
            if high_reflectivity_data:
                avg_sr_high = sum(d['lidar_sr_range_m'] for d in high_reflectivity_data) / len(high_reflectivity_data)
                f.write(f"  Hohe Reflektivität (>0.7): {avg_sr_high:.1f} m\n")
            else:
                f.write(f"  Hohe Reflektivität (>0.7): N/A\n")
            
            # Kamera
            f.write("Kamera:\n")
            if low_reflectivity_data:
                avg_cam_low = sum(d['camera_effective_range_m'] for d in low_reflectivity_data) / len(low_reflectivity_data)
                f.write(f"  Niedrige Reflektivität (<0.3): {avg_cam_low:.1f} m\n")
            else:
                f.write(f"  Niedrige Reflektivität (<0.3): N/A\n")
            
            if medium_reflectivity_data:
                avg_cam_medium = sum(d['camera_effective_range_m'] for d in medium_reflectivity_data) / len(medium_reflectivity_data)
                f.write(f"  Mittlere Reflektivität (0.3-0.7): {avg_cam_medium:.1f} m\n")
            else:
                f.write(f"  Mittlere Reflektivität (0.3-0.7): N/A\n")
            
            if high_reflectivity_data:
                avg_cam_high = sum(d['camera_effective_range_m'] for d in high_reflectivity_data) / len(high_reflectivity_data)
                f.write(f"  Hohe Reflektivität (>0.7): {avg_cam_high:.1f} m\n")
            else:
                f.write(f"  Hohe Reflektivität (>0.7): N/A\n")
        
        if weather_condition == "DenseFog":
            f.write("\nSystemlimitierung: Bei dichtem Nebel ist die Wahrnehmungsleistung stark eingeschränkt, ")
            f.write("was zu erhöhten Risiken für die autonome Fahrfunktion führt. ")
            f.write("Die Notbremsstrategie ist eine notwendige Sicherheitsmaßnahme bei kritisch reduzierter Wahrnehmung.\n")
    
    print(f"Bericht gespeichert: {filename}")

# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Hauptfunktion - führt Simulationen für beide Wetterbedingungen durch"""
    
    print("=== L5 Autonomes Fahrzeug Simulation - Radarausfall auf Autobahn ===")
    print(f"Simulationsparameter:")
    print(f"- Anfangsgeschwindigkeit: {INITIAL_SPEED_KMH} km/h")
    print(f"- Verzögerungsrate: {DECELERATION_RATE_MPS2} m/s²")
    print(f"- Zeitschritt: {TIME_STEP_S} s")
    print(f"- Sensor Fusion Verzögerung: {SENSOR_FUSION_DELAY_S} s")
    
    # Ausgabepfad anzeigen
    output_path = create_output_directory()
    print(f"Ausgabeverzeichnis: {output_path}")
    
    # Simulationen für beide Wetterbedingungen
    weather_conditions = ["Normal", "DenseFog"]
    
    for weather in weather_conditions:
        print(f"\n{'='*50}")
        print(f"Simulation für Wetterbedingung: {weather}")
        print(f"{'='*50}")
        
        # Simulation durchführen
        simulation_data, events_log = run_simulation(weather)
        
        # Ergebnisse speichern
        save_csv_data(weather, simulation_data)
        save_report(weather, events_log, simulation_data)
        
        print(f"Simulation für {weather} abgeschlossen.")
    
    print(f"\n{'='*50}")
    print("Alle Simulationen abgeschlossen!")
    print(f"Ergebnisse im Verzeichnis '{output_path}' gespeichert.")
    print(f"{'='*50}")

if __name__ == "__main__":
    main()