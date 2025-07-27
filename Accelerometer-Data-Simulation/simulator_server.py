import pygame
import threading
import time
from flask import Flask, request, jsonify
import sys

# === CONFIGURATION ===
SERVER_HOST = "0.0.0.0"  # Listen on all interfaces
SERVER_PORT = 5000

# === Robot state ===
robot_command = "S"
command_lock = threading.Lock()

# === Flask web server ===
app = Flask(__name__)

# === Pygame settings ===
WIDTH, HEIGHT = 800, 600
ROBOT_SIZE = 40
FPS = 60
robot_pos = [WIDTH // 2, HEIGHT // 2]
robot_speed = 4


@app.route('/command')
def receive_command():
    """Receive commands from ESP8266"""
    global robot_command

    cmd = request.args.get('cmd', 'S')

    with command_lock:
        robot_command = cmd

    print(f"📨 ESP8266 -> {cmd}")
    return jsonify({"status": "success", "command": cmd, "timestamp": time.time()})


@app.route('/')
def status():
    """Status page"""
    with command_lock:
        current_cmd = robot_command

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>🤖 Robot Control Server</title>
        <meta http-equiv="refresh" content="2">
        <style>
            body {{ background: #1a1a1a; color: #fff; font-family: Arial; margin: 40px; }}
            .status {{ background: #2a2a2a; padding: 20px; border-radius: 10px; }}
            .cmd {{ font-size: 24px; color: #0f0; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="status">
            <h1>🤖 Robot Control Server</h1>
            <p class="cmd">Current Command: {current_cmd}</p>
            <p><strong>Server:</strong> {SERVER_HOST}:{SERVER_PORT}</p>
            <p><strong>Commands:</strong></p>
            <ul>
                <li><strong>F</strong> = Forward</li>
                <li><strong>B</strong> = Backward</li>
                <li><strong>L</strong> = Left</li>
                <li><strong>R</strong> = Right</li>
                <li><strong>S</strong> = Stop</li>
            </ul>
            <p>🎮 Tilt your ESP8266 device to control the robot!</p>
            <p>⌨️ Or use WASD keys in the pygame window</p>
        </div>
    </body>
    </html>
    """


def run_flask_server():
    """Run Flask server in a separate thread"""
    print(f"🚀 Starting Flask server on {SERVER_HOST}:{SERVER_PORT}")
    try:
        app.run(host=SERVER_HOST, port=SERVER_PORT, debug=False, use_reloader=False, threaded=True)
    except Exception as e:
        print(f"❌ Flask server error: {e}")


def simulate():
    """Main pygame simulation with improved movement"""
    global robot_command

    # Initialize pygame
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("🤖 ESP8266 Tilt Robot Simulator")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 20, bold=True)
    font_small = pygame.font.SysFont("Arial", 16)

    # Colors
    BLACK = (0, 0, 0)
    WHITE = (255, 255, 255)
    GREEN = (0, 255, 0)
    RED = (255, 0, 0)
    BLUE = (0, 100, 255)
    YELLOW = (255, 255, 0)
    GRAY = (100, 100, 100)

    # Robot physics
    robot_velocity = [0.0, 0.0]
    acceleration = 0.6
    max_speed = robot_speed
    friction = 0.92

    # Trail system
    trail_points = []
    max_trail = 150

    # Debug info
    last_command_time = time.time()
    command_count = 0

    print("🎮 Pygame simulation started!")
    print("💡 Tilt ESP8266 or use WASD keys to control")

    running = True
    while running:
        dt = clock.tick(FPS)

        # Handle pygame events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                # Manual keyboard control for testing
                with command_lock:
                    if event.key == pygame.K_w:
                        robot_command = "F"
                        print("🎮 Manual: Forward")
                    elif event.key == pygame.K_s:
                        robot_command = "B"
                        print("🎮 Manual: Backward")
                    elif event.key == pygame.K_a:
                        robot_command = "L"
                        print("🎮 Manual: Left")
                    elif event.key == pygame.K_d:
                        robot_command = "R"
                        print("🎮 Manual: Right")
                    elif event.key == pygame.K_SPACE:
                        robot_command = "S"
                        print("🎮 Manual: Stop")

        # Get current command safely
        with command_lock:
            current_cmd = robot_command

        # Calculate target velocity based on command
        target_vel = [0.0, 0.0]
        if current_cmd == "F":
            target_vel[1] = -max_speed
        elif current_cmd == "B":
            target_vel[1] = max_speed
        elif current_cmd == "L":
            target_vel[0] = -max_speed
        elif current_cmd == "R":
            target_vel[0] = max_speed
        # "S" means target_vel remains [0, 0]

        # Smooth velocity changes
        for i in range(2):
            if target_vel[i] != 0:
                # Accelerate towards target
                if robot_velocity[i] < target_vel[i]:
                    robot_velocity[i] = min(target_vel[i], robot_velocity[i] + acceleration)
                elif robot_velocity[i] > target_vel[i]:
                    robot_velocity[i] = max(target_vel[i], robot_velocity[i] - acceleration)
            else:
                # Apply friction when no input
                robot_velocity[i] *= friction
                if abs(robot_velocity[i]) < 0.1:
                    robot_velocity[i] = 0

        # Update robot position
        old_pos = robot_pos.copy()
        robot_pos[0] += robot_velocity[0]
        robot_pos[1] += robot_velocity[1]

        # Boundary collision with bounce
        if robot_pos[0] <= ROBOT_SIZE // 2:
            robot_pos[0] = ROBOT_SIZE // 2
            robot_velocity[0] = abs(robot_velocity[0]) * 0.7
        elif robot_pos[0] >= WIDTH - ROBOT_SIZE // 2:
            robot_pos[0] = WIDTH - ROBOT_SIZE // 2
            robot_velocity[0] = -abs(robot_velocity[0]) * 0.7

        if robot_pos[1] <= ROBOT_SIZE // 2:
            robot_pos[1] = ROBOT_SIZE // 2
            robot_velocity[1] = abs(robot_velocity[1]) * 0.7
        elif robot_pos[1] >= HEIGHT - ROBOT_SIZE // 2:
            robot_pos[1] = HEIGHT - ROBOT_SIZE // 2
            robot_velocity[1] = -abs(robot_velocity[1]) * 0.7

        # Add to trail
        if abs(robot_pos[0] - old_pos[0]) > 0.5 or abs(robot_pos[1] - old_pos[1]) > 0.5:
            trail_points.append(old_pos.copy())
            if len(trail_points) > max_trail:
                trail_points.pop(0)

        # === DRAWING ===
        screen.fill(BLACK)

        # Draw grid
        for x in range(0, WIDTH, 50):
            pygame.draw.line(screen, (20, 20, 20), (x, 0), (x, HEIGHT))
        for y in range(0, HEIGHT, 50):
            pygame.draw.line(screen, (20, 20, 20), (0, y), (WIDTH, y))

        # Draw trail
        for i, point in enumerate(trail_points):
            alpha_factor = (i + 1) / len(trail_points)
            size = max(1, int(ROBOT_SIZE * alpha_factor * 0.3))
            color_intensity = int(100 * alpha_factor)
            trail_color = (0, color_intensity, 50)
            pygame.draw.circle(screen, trail_color, [int(point[0]), int(point[1])], size)

        # Calculate robot color based on speed
        speed_magnitude = (robot_velocity[0] ** 2 + robot_velocity[1] ** 2) ** 0.5
        speed_ratio = min(1.0, speed_magnitude / max_speed)

        robot_color = (
            int(speed_ratio * 255),  # Red increases with speed
            int((1 - speed_ratio) * 255),  # Green decreases with speed
            50  # Constant blue
        )

        # Draw robot
        robot_rect = pygame.Rect(
            int(robot_pos[0] - ROBOT_SIZE // 2),
            int(robot_pos[1] - ROBOT_SIZE // 2),
            ROBOT_SIZE,
            ROBOT_SIZE
        )
        pygame.draw.rect(screen, robot_color, robot_rect)
        pygame.draw.rect(screen, WHITE, robot_rect, 3)

        # Draw velocity vector
        if speed_magnitude > 0.5:
            end_x = robot_pos[0] + robot_velocity[0] * 5
            end_y = robot_pos[1] + robot_velocity[1] * 5
            pygame.draw.line(screen, YELLOW,
                             [int(robot_pos[0]), int(robot_pos[1])],
                             [int(end_x), int(end_y)], 4)

        # Draw command indicator
        indicator_pos = [robot_pos[0], robot_pos[1] - ROBOT_SIZE]
        if current_cmd == "F":
            pygame.draw.polygon(screen, WHITE, [
                [indicator_pos[0], indicator_pos[1] - 15],
                [indicator_pos[0] - 8, indicator_pos[1] - 5],
                [indicator_pos[0] + 8, indicator_pos[1] - 5]
            ])
        elif current_cmd == "B":
            pygame.draw.polygon(screen, WHITE, [
                [indicator_pos[0], indicator_pos[1] + 35],
                [indicator_pos[0] - 8, indicator_pos[1] + 25],
                [indicator_pos[0] + 8, indicator_pos[1] + 25]
            ])
        elif current_cmd == "L":
            pygame.draw.polygon(screen, WHITE, [
                [indicator_pos[0] - 25, indicator_pos[1] + 10],
                [indicator_pos[0] - 15, indicator_pos[1] + 2],
                [indicator_pos[0] - 15, indicator_pos[1] + 18]
            ])
        elif current_cmd == "R":
            pygame.draw.polygon(screen, WHITE, [
                [indicator_pos[0] + 25, indicator_pos[1] + 10],
                [indicator_pos[0] + 15, indicator_pos[1] + 2],
                [indicator_pos[0] + 15, indicator_pos[1] + 18]
            ])

        # === UI INFO ===
        # Command display
        cmd_text = font.render(f"Command: {current_cmd}", True, WHITE)
        screen.blit(cmd_text, (10, 10))

        # Position
        pos_text = font_small.render(f"Position: ({int(robot_pos[0])}, {int(robot_pos[1])})", True, GRAY)
        screen.blit(pos_text, (10, 40))

        # Velocity
        vel_text = font_small.render(f"Velocity: ({robot_velocity[0]:.1f}, {robot_velocity[1]:.1f})", True, GRAY)
        screen.blit(vel_text, (10, 60))

        # Speed
        speed_text = font_small.render(f"Speed: {speed_magnitude:.1f}", True, GRAY)
        screen.blit(speed_text, (10, 80))

        # Server info
        server_text = font_small.render(f"Server: {SERVER_HOST}:{SERVER_PORT}", True, GRAY)
        screen.blit(server_text, (10, 100))

        # Instructions
        help_text = font_small.render("Tilt ESP8266 to control | WASD for manual | ESC to quit", True, (150, 150, 150))
        screen.blit(help_text, (10, HEIGHT - 25))

        # Update display
        pygame.display.flip()

    pygame.quit()
    print("🛑 Pygame simulation ended")


def main():
    """Main function with better error handling"""
    print("=" * 60)
    print("🤖 ESP8266 Tilt-Controlled Robot Server v2.0")
    print("=" * 60)

    # Start Flask server in background
    try:
        server_thread = threading.Thread(target=run_flask_server, daemon=True)
        server_thread.start()
        print("✅ Flask server thread started")

        # Give server time to start
        time.sleep(1)

        print(f"📡 Server ready at http://localhost:{SERVER_PORT}")
        print(f"🎯 ESP8266 should send to: http://YOUR_COMPUTER_IP:{SERVER_PORT}/command?cmd=X")
        print("🎮 Starting pygame simulation...")

        # Start pygame in main thread
        simulate()

    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

    print("👋 Server shutdown complete")


if __name__ == "__main__":
    main()