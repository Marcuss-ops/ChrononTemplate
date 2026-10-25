# Green-screen hand finger-rig proof V1

## Scene contract

- **Subject and asset:** A photoreal right palm and wrist, fingers extended, from `assets/social_rig_proof_v1/processed/hand_keyed.png` (1024×1536 RGBA after chroma key).
- **Composition/camera:** Static orthographic front view; wrist and all fingertips remain inside frame over a pure #00FF00 background.
- **Motion/timing:** Three-second action. Start open, curl fingers into a fist, briefly hold, then extend. Palm and wrist stay fixed.
- **Rig/layers:** C++ creates a dense textured plane with a real SkinnedMesh/Skeleton. Palm is the root; thumb and four fingers each have proximal, middle and distal bones. Vertex weights blend at the joints. No hand or finger masks are used for motion.
- **Must not appear:** Extra fingers, broken joints, green gaps inside the palm, duplicated digits, palm/wrist motion, camera motion or background shadows.
- **Review:** Compare open, mid-curl, closed, reopening and final frames. Confirm every digit changes through its joint chain and the palm stays fixed.
