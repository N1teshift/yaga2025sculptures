#!/usr/bin/liquidsoap

# Liquidsoap main configuration for sculpture system
# Creates personalized mixes for each sculpture

# Set log level
settings.log.level := 3

# Enable telnet server for control
settings.server.telnet := true
settings.server.telnet.bind_addr := "0.0.0.0"
settings.server.telnet.port := 1234
settings.server.telnet.password := "admin"

# Enable HTTP server for API
settings.server.socket := true
settings.server.socket.path := "/tmp/liquidsoap.sock"
settings.server.socket.permissions := 0o600

# Audio settings
settings.frame.audio.samplerate := 48000
settings.frame.audio.channels := 1

# Input sources from sculptures
# These will be the live microphone feeds from each sculpture
let a1 = input.http(
  id="sculpture1_input",
  "http://localhost:8000/s1-mic.ogg"
)

let a2 = input.http(
  id="sculpture2_input", 
  "http://localhost:8000/s2-mic.ogg"
)

let a3 = input.http(
  id="sculpture3_input",
  "http://localhost:8000/s3-mic.ogg"
)

# Add fallback silence for when inputs are not available
let silence = blank(duration=1.0)

let a1_safe = fallback(id="a1_fallback", [a1, silence])
let a2_safe = fallback(id="a2_fallback", [a2, silence])
let a3_safe = fallback(id="a3_fallback", [a3, silence])

# Apply some basic audio processing
let process_audio = fun(s) ->
  # Normalize audio levels
  let s = normalize(target=-14.0, window=1.0, s)
  # Add slight compression
  let s = compress(attack=0.1, release=0.5, ratio=3.0, threshold=-12.0, s)
  # High-pass filter to remove low-frequency noise
  let s = filter.iir.butterworth.high(frequency=80.0, order=2, s)
  s
end

let a1_processed = process_audio(a1_safe)
let a2_processed = process_audio(a2_safe)
let a3_processed = process_audio(a3_safe)

# Create personalized mixes
# Each sculpture hears the other two sculptures, not itself
let to1 = add(normalize=false, [a2_processed, a3_processed])
let to2 = add(normalize=false, [a1_processed, a3_processed])
let to3 = add(normalize=false, [a1_processed, a2_processed])

# Apply final processing to mixes
let to1_final = process_audio(to1)
let to2_final = process_audio(to2)
let to3_final = process_audio(to3)

# Output function for Icecast
let mount = fun(mount_name, source) ->
  output.icecast(
    %opus(vbr=true, bitrate=128),
    host="localhost",
    port=8000,
    password="hackme",
    mount=mount_name,
    name="Sculpture Mix - " ^ mount_name,
    description="Personalized audio mix for sculpture installation",
    genre="ambient",
    url="http://sculpture.local",
    public=false,
    source
  )
end

# Create the output streams
mount("mix-for-1.ogg", to1_final)
mount("mix-for-2.ogg", to2_final)
mount("mix-for-3.ogg", to3_final)

# Log startup
log("Sculpture system Liquidsoap configuration loaded")
log("Telnet server available on port 1234 (password: admin)")
log("Creating personalized mixes:")
log("  - mix-for-1.ogg: sculptures 2+3 for sculpture 1")
log("  - mix-for-2.ogg: sculptures 1+3 for sculpture 2") 
log("  - mix-for-3.ogg: sculptures 1+2 for sculpture 3") 