# Liquidsoap presets and helper functions for sculpture system

# Audio processing presets
let sculpture_normalize = normalize.old(target=-14.0, window=1.0)

let sculpture_compress = compress(
  attack=0.1,
  release=0.5, 
  ratio=3.0,
  threshold=-12.0
)

let sculpture_highpass = filter.iir.butterworth.high(
  frequency=80.0,
  order=2
)

let sculpture_lowpass = filter.iir.butterworth.low(
  frequency=8000.0,
  order=2
)

# Combined processing chain
let sculpture_process = fun(s) ->
  let s = sculpture_normalize(s)
  let s = sculpture_compress(s)
  let s = sculpture_highpass(s)
  let s = sculpture_lowpass(s)
  s
end

# Crossfade function for smooth transitions
let sculpture_crossfade = crossfade(
  duration=2.0,
  fade_in=1.0,
  fade_out=1.0
)

# Smart fallback with logging
let sculpture_fallback = fun(id, sources) ->
  fallback(
    id=id,
    track_sensitive=false,
    sources
  )
end

# Volume control function
let sculpture_volume = fun(vol, s) ->
  amplify(vol, s)
end

# Stereo to mono conversion
let to_mono = fun(s) ->
  mean(s)
end

# Add reverb effect
let sculpture_reverb = fun(s) ->
  let dry = s
  let wet = reverb(room_size=0.3, damping=0.5, wet=0.2, dry=0.8, s)
  add(normalize=false, [dry, wet])
end

# Delay effect
let sculpture_delay = fun(delay_time, feedback, s) ->
  let delayed = delay(delay_time, s)
  let feedback_signal = amplify(feedback, delayed)
  add(normalize=false, [s, feedback_signal])
end

# Dynamic range compressor specifically for ambient audio
let ambient_compress = compress(
  attack=0.5,
  release=2.0,
  ratio=2.0,
  threshold=-18.0
)

# Gate to remove very quiet noise
let sculpture_gate = fun(threshold, s) ->
  gate(threshold=threshold, s)
end

# Smooth volume automation
let sculpture_fade_in = fade.in(duration=3.0)
let sculpture_fade_out = fade.out(duration=3.0)

# Emergency silence generator
let emergency_silence = blank(duration=1.0)

# Test tone generator (for debugging)
let test_tone = fun(freq) ->
  sine(freq)
end

# Log helper
let sculpture_log = fun(msg) ->
  log(label="sculpture", msg)
end 