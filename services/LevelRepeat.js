.pragma library

function multiplier(elapsed) {
    return elapsed >= 1800 ? 5 : elapsed >= 1000 ? 3 : elapsed >= 600 ? 2 : 1;
}

// Some laptop hotkeys deliver repeated press/release pulses instead of a held key.
function begin(previous, direction, now) {
    const continuing = previous && previous.direction === direction
        && now >= previous.ended && now - previous.ended < 180;
    return {direction: direction, since: continuing ? previous.since : now};
}
