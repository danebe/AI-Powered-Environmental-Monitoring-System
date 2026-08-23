"""
Generate authentic EAS & Emergency Siren WAV audio files for the Dashboard
"""

import wave
import struct
import math
import os

def create_wav(filepath, duration_sec, sample_rate=44100, generator_fn=None):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    num_samples = int(duration_sec * sample_rate)
    
    with wave.open(filepath, 'w') as wav:
        wav.setnchannels(1) # Mono
        wav.setsampwidth(2) # 16-bit
        wav.setframerate(sample_rate)
        
        frames = bytearray()
        for i in range(num_samples):
            t = float(i) / sample_rate
            sample_val = generator_fn(t, duration_sec)
            # Clamp to -1.0 to 1.0
            sample_val = max(-1.0, min(1.0, sample_val))
            int_val = int(sample_val * 32767.0 * 0.4) # Safe volume
            frames.extend(struct.pack('<h', int_val))
            
        wav.writeframes(frames)
    print(f"Generated {filepath}")

# 1. EAS Warning: Authentic 853 Hz + 960 Hz Attention Signal
def gen_eas_warning(t, duration):
    # Envelope: gentle fade in and fade out
    env = 1.0
    if t < 0.05: env = t / 0.05
    elif t > duration - 0.05: env = (duration - t) / 0.05
    
    s1 = math.sin(2.0 * math.pi * 853.0 * t)
    s2 = math.sin(2.0 * math.pi * 960.0 * t)
    return (s1 + s2) * 0.5 * env

# 2. EAS Flood Siren: EAS Attention Tone followed by continuous rising/falling Air Raid siren
def gen_eas_flood(t, duration):
    if t < 1.2:
        # EAS Attention tone intro
        s1 = math.sin(2.0 * math.pi * 853.0 * t)
        s2 = math.sin(2.0 * math.pi * 960.0 * t)
        return (s1 + s2) * 0.5
    else:
        # Air raid siren pitch ramp (280 Hz to 720 Hz)
        t_rel = t - 1.2
        cycle = math.sin(2.0 * math.pi * 0.4 * t_rel) # 0.4 Hz cycle
        freq = 500.0 + (220.0 * cycle)
        return math.sin(2.0 * math.pi * freq * t)

# 3. EAS Wildfire Siren: EAS Attention Tone + Rapid Thermal Alarm pulses
def gen_eas_fire(t, duration):
    if t < 1.0:
        s1 = math.sin(2.0 * math.pi * 853.0 * t)
        s2 = math.sin(2.0 * math.pi * 960.0 * t)
        return (s1 + s2) * 0.5
    else:
        # Rapid urgent thermal pulses (800Hz / 1100Hz alternating every 0.15s)
        t_rel = t - 1.0
        step = int(t_rel / 0.15) % 2
        freq = 1100.0 if step == 1 else 780.0
        env = math.exp(-3.0 * (t_rel % 0.15))
        return math.sin(2.0 * math.pi * freq * t) * (0.6 + 0.4 * env)

# 4. EAS Chemical / Gas Leak Siren: EAS Attention Tone + High-pitch Hazmat sweeps
def gen_eas_gas(t, duration):
    if t < 1.0:
        s1 = math.sin(2.0 * math.pi * 853.0 * t)
        s2 = math.sin(2.0 * math.pi * 960.0 * t)
        return (s1 + s2) * 0.5
    else:
        # Staccato Hazmat double-beeps (1400 Hz / 1650 Hz)
        t_rel = t - 1.0
        sub_t = t_rel % 0.4
        if sub_t < 0.12:
            return math.sin(2.0 * math.pi * 1400.0 * t)
        elif sub_t < 0.24:
            return math.sin(2.0 * math.pi * 1650.0 * t)
        else:
            return 0.0

if __name__ == "__main__":
    sounds_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dashboard", "sounds")
    create_wav(os.path.join(sounds_dir, "eas_warning.wav"), duration_sec=1.5, generator_fn=gen_eas_warning)
    create_wav(os.path.join(sounds_dir, "eas_flood.wav"), duration_sec=4.0, generator_fn=gen_eas_flood)
    create_wav(os.path.join(sounds_dir, "eas_fire.wav"), duration_sec=3.5, generator_fn=gen_eas_fire)
    create_wav(os.path.join(sounds_dir, "eas_gas.wav"), duration_sec=3.5, generator_fn=gen_eas_gas)
