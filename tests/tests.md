# Unit Tests Overview

This document provides an overview of the test suite for the LumenTrace project. The tests validate core functionality across the game engine, display system, input handling, and audio components.

These tests were instrumental during the development phase for validating physics behavior, LED rendering logic, and controller integration. While some tests may require maintenance due to code evolution, they remain a valuable reference for understanding the intended behavior of core systems.

## Test Structure

The test suite is organized by module, mirroring the source code architecture:

### Controller Tests (`controller_test/`)

Tests for the input signal handling and controller interface:

- **Signal receiver initialization and data structure validation**
- Controller state management and signal payload formats
- Mock controller behavior for deterministic testing

### Display Tests (`display_test/`)

Tests for LED display rendering and visual effects:

- **Display hierarchy validation** - Verifies correct layering of track modules, vehicles, and visual effects
- Virtual LED strip buffer management and color mapping
- Vehicle position rendering with speed-based color indicators
- Round advance animations and lane change visual feedback
- Intersection lane rendering

### Game Tests (`game_test/`)

High-fidelity physics and game logic validation:

- **Lane change mechanics** - Multi-hop changes, position conversion proportionality, end-window blocking
- **Vehicle kinematics** - Friction, acceleration, speed updates, and position wrapping
- **Driving profile enforcement** - Speed and acceleration boundary checking across module transitions
- **Lane gap detection** - Fall triggering when crossing missing lanes between modules
- **Collision detection** - Same-lane rear-end collision handling
- **Respawn behavior** - Lane occupation checks, round preservation, and spawn position selection

These tests provide high-signal validation of core game rules described in the project README.

### Display Manager Tests (`display_test/`)

Integration tests for game state to visual representation:

- Vehicle active state and respawn ticking color blending
- Track module boundary visualization
- Round advance cycle animations with timing verification

### Sound Tests (`sound_test/`)

Audio system validation:

- Sound manager initialization and audio stream setup
- Master volume clamping and control
- Active sound tracking and playback management

### Simulation Tests (`simulation_test/`)

*Note: Most simulation tests are currently commented out. They were used during development for local terminal visualization and deterministic behavior validation but may require updates due to API changes.*

## Running the Tests

Execute tests using pytest:

```bash
pytest tests/
```

To run tests for a specific module:

```bash
pytest tests/game_test/
pytest tests/display_test/
pytest tests/controller_test/
```
