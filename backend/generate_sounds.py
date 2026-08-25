"""
Generate authentic EAS & Emergency Siren WAV audio files for the Dashboard
Professional DSP phase-accumulator synthesis for authentic civil defense sirens
"""

import wave
import struct
import math
import os

def create_wav_raw(filepath, duration_sec, sample_rate, frames_bytes):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with wave.open(filepath, 'w') as wav:
        wav.setnchannels(1) # Mono
        wav.setsampwidth(2) # 16-bit
        wav.setframerate(sample_rate)
        wav.writeframes(frames_bytes)
    print(f"Generated {filepath} ({duration_sec}s)")

# 1. EAS Attention Signal: Authentic FCC 853 Hz + 960 Hz Dual Tone
def gen_eas_warning(duration_sec=2.0, sample_rate=44100):
    num_samples = int(duration_sec * sample_rate)
    frames = bytearray()
    dt = 1.0 / sample_rate
    p1 = 0.0
    p2 = 0.0
    for i in range(num_samples):
        t = float(i) / sample_rate
        env = min(1.0, t / 0.08) * min(1.0, (duration_sec - t) / 0.08)
        p1 += 2.0 * math.pi * 853.0 * dt
        p2 += 2.0 * math.pi * 960.0 * dt
        s = 0.5 * (math.sin(p1) + math.sin(p2)) * env
        int_val = int(max(-1.0, min(1.0, s)) * 32767.0 * 0.45)
        frames.extend(struct.pack('<h', int_val))
    return frames

# 2. Authentic Civil Defense / Air Raid Siren (Dual-Rotor Mechanical Tone Sweep)
def gen_eas_flood(duration_sec=10.0, sample_rate=44100):
    num_samples = int(duration_sec * sample_rate)
    dt = 1.0 / sample_rate
    
    phase_main = 0.0
    phase_harm = 0.0
    phase_sub  = 0.0
    phase_over = 0.0
    
    frames = bytearray()
    for i in range(num_samples):
        t = float(i) / sample_rate
        
        # 4.0s period civil defense wail cycle (undulates 350 Hz -> 750 Hz)
        cycle = (math.sin(2.0 * math.pi * 0.25 * t - (math.pi / 2.0)) + 1.0) * 0.5
        cycle_curved = cycle ** 1.3
        
        # Smooth motor spin-up (1.2s) and spin-down (1.8s)
        attack = min(1.0, t / 1.2)
        release = min(1.0, (duration_sec - t) / 1.8) if duration_sec > t else 0.0
        env = attack * release
        
        # Instantaneous rotor speed
        freq = (350.0 + 400.0 * cycle_curved) * (0.6 + 0.4 * attack) * (0.5 + 0.5 * release)
        
        # Phase integration (eliminates all frequency distortion/glitches)
        phase_main += 2.0 * math.pi * freq * dt
        phase_harm += 2.0 * math.pi * (freq * 1.5) * dt  # 12-port to 8-port perfect fifth ratio
        phase_sub  += 2.0 * math.pi * (freq * 0.5) * dt  # Sub-harmonic chassis resonance
        phase_over += 2.0 * math.pi * (freq * 2.0) * dt  # 2nd harmonic
        
        # Ported air-pulse saturation (soft odd harmonics)
        s_main = math.sin(phase_main) + 0.15 * math.sin(3.0 * phase_main)
        s_harm = 0.40 * (math.sin(phase_harm) + 0.10 * math.sin(3.0 * phase_harm))
        s_sub  = 0.20 * math.sin(phase_sub)
        s_over = 0.12 * math.sin(phase_over)
        
        # 12Hz mechanical motor rumble
        motor_rumble = 0.88 + 0.12 * math.sin(2.0 * math.pi * 12.0 * t)
        
        sample = (s_main + s_harm + s_sub + s_over) * motor_rumble * env * 0.70
        int_val = int(max(-1.0, min(1.0, sample)) * 32767.0 * 0.55)
        frames.extend(struct.pack('<h', int_val))
        
    return frames

# 3. Wildfire / Extreme Hazard Hi-Lo Klaxon
def gen_eas_fire(duration_sec=4.0, sample_rate=44100):
    num_samples = int(duration_sec * sample_rate)
    dt = 1.0 / sample_rate
    frames = bytearray()
    phase = 0.0
    for i in range(num_samples):
        t = float(i) / sample_rate
        env = min(1.0, t / 0.1) * min(1.0, (duration_sec - t) / 0.2)
        freq = 1050.0 if (int(t / 0.35) % 2 == 0) else 780.0
        phase += 2.0 * math.pi * freq * dt
        pulse_decay = 0.6 + 0.4 * math.exp(-3.0 * (t % 0.35))
        s = math.sin(phase) * pulse_decay * env
        int_val = int(max(-1.0, min(1.0, s)) * 32767.0 * 0.50)
        frames.extend(struct.pack('<h', int_val))
    return frames

# 4. Toxic Gas / Industrial Chemical Alarm
def gen_eas_gas(duration_sec=4.0, sample_rate=44100):
    num_samples = int(duration_sec * sample_rate)
    dt = 1.0 / sample_rate
    frames = bytearray()
    p1 = 0.0
    p2 = 0.0
    for i in range(num_samples):
        t = float(i) / sample_rate
        env = min(1.0, t / 0.1) * min(1.0, (duration_sec - t) / 0.2)
        sub_t = t % 0.4
        p1 += 2.0 * math.pi * 1400.0 * dt
        p2 += 2.0 * math.pi * 1650.0 * dt
        if sub_t < 0.14:
            s = math.sin(p1) * env
        elif sub_t < 0.28:
            s = math.sin(p2) * env
        else:
            s = 0.0
        int_val = int(max(-1.0, min(1.0, s)) * 32767.0 * 0.50)
        frames.extend(struct.pack('<h', int_val))
    return frames

if __name__ == "__main__":
    sounds_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dashboard", "sounds")
    create_wav_raw(os.path.join(sounds_dir, "eas_warning.wav"), 2.0,  44100, gen_eas_warning(2.0, 44100))
    create_wav_raw(os.path.join(sounds_dir, "eas_flood.wav"),   10.0, 44100, gen_eas_flood(10.0, 44100))
    create_wav_raw(os.path.join(sounds_dir, "eas_fire.wav"),    4.0,  44100, gen_eas_fire(4.0, 44100))
    create_wav_raw(os.path.join(sounds_dir, "eas_gas.wav"),     4.0,  44100, gen_eas_gas(4.0, 44100))
