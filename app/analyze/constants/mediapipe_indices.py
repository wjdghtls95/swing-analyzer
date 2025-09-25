# MediaPipe Pose landmark indices
L_SHOULDER, R_SHOULDER = 11, 12
L_ELBOW,   R_ELBOW     = 13, 14
L_WRIST,   R_WRIST     = 15, 16
L_HIP,     R_HIP       = 23, 24
L_KNEE,    R_KNEE      = 25, 26
L_ANKLE,   R_ANKLE     = 27, 28
NOSE                     = 0

# Triplets for joint angles
RIGHT_ARM = (R_SHOULDER, R_ELBOW, R_WRIST)
LEFT_ARM  = (L_SHOULDER, L_ELBOW, L_WRIST)

RIGHT_LEG = (R_HIP, R_KNEE, R_ANKLE)
LEFT_LEG  = (L_HIP, L_KNEE, L_ANKLE)

# Standard swing phases (keys)
PHASE_KEYS = ("P2", "P4", "P5", "P7", "P8", "P9")