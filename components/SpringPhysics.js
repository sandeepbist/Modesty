.pragma library

function step(value, velocity, target, seconds, frequency, dampingRatio) {
    const omega = 2 * Math.PI * frequency;
    const error = value - target;
    const decay = Math.exp(-dampingRatio * omega * seconds);
    if (dampingRatio < 1) {
        const damped = omega * Math.sqrt(1 - dampingRatio * dampingRatio);
        const cosine = Math.cos(damped * seconds);
        const sine = Math.sin(damped * seconds);
        return [target + decay * (error * cosine + (velocity + dampingRatio * omega * error) / damped * sine),
                decay * (velocity * cosine - (dampingRatio * omega * velocity + omega * omega * error) / damped * sine)];
    }
    const slope = velocity + omega * error;
    return [target + (error + slope * seconds) * decay,
            (velocity - omega * slope * seconds) * decay];
}
