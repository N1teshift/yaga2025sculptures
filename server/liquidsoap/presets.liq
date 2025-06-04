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
  sculpture_lowpass(
    sculpture_highpass(
      sculpture_compress(
        sculpture_normalize(s)
      )
    )
  )

# Crossfade function for smooth transitions
let sculpture_crossfade = crossfade(
  duration=2.0,
  fade_in=1.0,
  fade_out=1.0
)

# Smart fallback with logging when fallback sources become active
def sculpture_fallback(id, sources) =
  def wrap(idx, items) =
    if items == [] then []
    else
      src  = list.hd(items)
      rest = list.tl(items)
      logged =
        if idx > 1 then
          on_start(src, fun () ->
            sculpture_log("Fallback #{id} activated (source #{idx})")
          )
        else
          src
        end
      logged :: wrap(idx + 1, rest)
    end
  end
  fallback(
    id=id,
    track_sensitive=false,
    wrap(1, sources)
  )
end

# Volume control function
let sculpture_volume = fun(vol, s) ->
  amplify(vol, s)

# Stereo to mono conversion
let to_mono = fun(s) ->
  mean(s)


# Delay effect
let sculpture_delay = fun(delay_time, feedback, s) ->
  add(normalize=false, [
    s,
    amplify(feedback, delay(delay_time, s))
  ])

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

# Smooth volume automation
let sculpture_fade_in = fade.in(duration=3.0)
let sculpture_fade_out = fade.out(duration=3.0)

# Emergency silence generator
let emergency_silence = blank(duration=1.0)

# Test tone generator (for debugging)
let test_tone = fun(freq) ->
  sine(freq)

# Log helper
let sculpture_log = fun(msg) ->
  log(label="sculpture", msg) 
