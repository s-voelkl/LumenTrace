"""Terminal renderer for live game simulation state."""

from src.game.game import Game
from src.game.lane import Lane
from src.game.track_module import TrackModule


class TerminalSimulationRenderer:
    """Render game state as a readable terminal dashboard.

    The renderer is intentionally text based (stdlib only) so it can run in any
    development shell without graphics setup.
    """

    _ANSI_RESET = "\x1b[0m"
    _ANSI_DIM = "\x1b[2m"
    _ANSI_YELLOW = "\x1b[33m"
    _ANSI_GREEN = "\x1b[32m"
    _ANSI_CYAN = "\x1b[36m"
    _ANSI_RED_BOLD = "\x1b[1;31m"
    _ANSI_BLUE_BOLD = "\x1b[1;34m"

    def __init__(self, track_width_chars: int = 72, max_event_lines: int = 18, use_color: bool = True) -> None:
        self.__track_width_chars = max(24, track_width_chars)
        self.__max_event_lines = max(5, max_event_lines)
        self.__use_color = use_color

    def render_frame(self, game: Game, tick: int, show_logs: bool = True) -> str:
        """Build one complete dashboard frame.

        Args:
            game (Game): Active game instance.
            tick (int): Current simulation tick.

        Returns:
            str: Multi-line dashboard text.
        """
        lines: list[str] = []
        lines.append("=" * 96)
        lines.append(f"LumenTrace Terminal Simulation | tick={tick} | track_length={game.length:.2f}")
        lines.append("=" * 96)
        lines.extend(self.__render_settings(game))
        lines.append("")
        lines.extend(self.__render_players(game))
        lines.append("")
        lines.extend(self.__render_track_modules(game))
        lines.append("")
        lines.extend(self.__render_visual_track(game))
        if show_logs:
            lines.append("")
            lines.extend(self.__render_event_log(game))
        return "\n".join(lines)

    def render_to_terminal(self, game: Game, tick: int) -> None:
        """Clear terminal and print latest frame."""
        frame = self.render_frame(game, tick, show_logs=False)
        print("\x1b[2J\x1b[H", end="")
        print(frame)

    def __render_settings(self, game: Game) -> list[str]:
        settings = game.settings
        return [
            "SETTINGS",
            (
                "  "
                f"max_speed={settings.max_speed:.2f} | "
                f"respawn_ticks={settings.respawn_ticks} | "
                f"friction_percent={settings.friction_percent:.3f} | "
                f"accel_multiplier={settings.acceleration_multiplier:.3f} | "
                f"special_1_threshold={settings.special_1_threshold:.2f} | "
                f"lane_change_ticks={settings.lane_change_ticks} | "
                f"vehicle_crash_distance={settings.vehicle_crash_distance:.2f}"
            ),
        ]

    def __render_players(self, game: Game) -> list[str]:
        out: list[str] = ["PLAYERS"]
        for index, player in enumerate(game.players, start=1):
            vehicle = player.vehicle
            lane_label = f"L{vehicle.lane.lane_id}" if vehicle.lane is not None else "None"
            module_text = "None"
            if vehicle.lane is not None:
                module_index, local_position = self.__resolve_lane_module_position(
                    game.track_modules,
                    vehicle.lane,
                    vehicle.position,
                )
                if module_index is not None:
                    module = game.track_modules[module_index]
                    module_text = (
                        f"{module_index}:{module.track_type.value}"
                        f"@{local_position:.2f}"
                    )

            out.append(
                (
                    f"  P{index} {player.name} | active={vehicle.active} | lane={lane_label} | "
                    f"pos={vehicle.position:.2f} | speed={vehicle.speed:.2f} | "
                    f"acc={vehicle.acceleration:.2f} | round={vehicle.round} | "
                    f"respawn={vehicle.respawn_ticks} | lane_change_ticks={vehicle.line_change_ticks} | "
                    f"target={self.__lane_target_label(vehicle.line_change_target)} | "
                    f"module={module_text}"
                )
            )
        return out

    def __render_track_modules(self, game: Game) -> list[str]:
        out: list[str] = ["TRACK MODULES"]
        for module_index, module in enumerate(game.track_modules):
            out.append(f"  M{module_index} {module.track_type.value} length={module.length:.2f}")
            for line in module.lines:
                profile = line.driving_profile
                out.append(
                    (
                        f"    lane=L{line.lane.lane_id} line_length={line.length:.2f} | "
                        f"v=[{profile.min_speed:.1f},{profile.max_speed:.1f}] | "
                        f"a=[{profile.min_acceleration:.1f},{profile.max_acceleration:.1f}] | "
                        f"lane_change_allowed={profile.lane_change_allowed}"
                    )
                )
        return out

    def __render_visual_track(self, game: Game) -> list[str]:
        out: list[str] = ["VISUAL TRACK (per lane)"]
        display_lanes = self.__get_display_lanes(game)
        module_spans = self.__module_spans_for_game(game)

        player_symbols: dict[Lane, dict[int, str]] = {}
        for player_index, player in enumerate(game.players, start=1):
            lane = player.vehicle.lane
            if not player.vehicle.active or lane is None:
                continue

            module_index, local_position = self.__resolve_lane_module_position(
                game.track_modules,
                lane,
                player.vehicle.position,
            )
            if module_index is None:
                continue

            line_length = game.track_modules[module_index].get_line_length_for_lane(lane)
            if line_length <= 0:
                continue

            start, end = module_spans[module_index]
            segment_width = max(1, end - start)
            progress = max(0.0, min(local_position / line_length, 1.0))
            char_index = start + min(segment_width - 1, int(progress * (segment_width - 1)))
            lane_symbols = player_symbols.setdefault(lane, {})
            lane_symbols[char_index] = self.__player_symbol(player_index)

        for lane in display_lanes:
            lane_length = self.__lane_track_length(game.track_modules, lane)
            if lane_length <= 0:
                out.append(f"  L{lane.lane_id}: (no drivable segments)")
                continue

            chars = [" "] * self.__track_width_chars
            for module_index, module in enumerate(game.track_modules):
                start, end = module_spans[module_index]
                line = module.get_line_for_lane(lane)
                if line is None:
                    continue

                segment_char = "=" if line.driving_profile.lane_change_allowed else "-"
                segment_color = self._ANSI_GREEN if line.driving_profile.lane_change_allowed else self._ANSI_CYAN
                for index in range(start, end):
                    chars[index] = self.__colorize(segment_char, segment_color)

            for start, _ in module_spans:
                if 0 <= start < self.__track_width_chars:
                    chars[start] = self.__colorize("|", self._ANSI_YELLOW)

            for char_index, symbol in player_symbols.get(lane, {}).items():
                chars[char_index] = symbol

            lane_bar = "".join(chars)
            out.append(f"  L{lane.lane_id} [{lane_bar}] len={lane_length:.2f}")

        out.append("  legend: '|' module boundary, '=' lane-change allowed, '-' lane-change blocked")
        out.append("          cyan=blocked lanes, green=lane-change lanes, red/blue=players")
        return out

    def __render_event_log(self, game: Game) -> list[str]:
        """Render event history so logs survive frame refreshes."""
        out: list[str] = ["EVENT LOG"]
        events = game.recent_events
        if not events:
            out.append("  no events yet")
            return out

        for event in events[-self.__max_event_lines:]:
            tick = event.get("tick", "?")
            event_name = event.get("event", "unknown")
            player = event.get("player")

            detail_parts: list[str] = []
            for key, value in event.items():
                if key in {"tick", "event", "player"}:
                    continue
                detail_parts.append(f"{key}={value}")

            message = f"  t={tick} | {event_name}"
            if player is not None:
                message += f" | player={player}"
            if detail_parts:
                message += " | " + ", ".join(detail_parts)
            out.append(message)

        return out

    @staticmethod
    def __get_display_lanes(game: Game) -> list[Lane]:
        """Return deterministic lane order for rendering.

        Uses configured game lanes first, then appends lanes that only appear in
        selected modules (for example temporary intersection lanes).
        """
        lanes: list[Lane] = []

        for lane in game.lanes:
            if lane not in lanes:
                lanes.append(lane)

        for module in game.track_modules:
            for line in module.lines:
                if line.lane not in lanes:
                    lanes.append(line.lane)

        return lanes

    @staticmethod
    def __lane_target_label(target_lane: Lane | None) -> str:
        return f"L{target_lane.lane_id}" if target_lane is not None else "None"

    def __colorize(self, text: str, color: str) -> str:
        if not self.__use_color:
            return text
        return f"{color}{text}{self._ANSI_RESET}"

    def __player_symbol(self, player_index: int) -> str:
        symbol = str(player_index)
        if player_index % 2 == 1:
            return self.__colorize(symbol, self._ANSI_RED_BOLD)
        return self.__colorize(symbol, self._ANSI_BLUE_BOLD)

    def __module_spans_for_game(self, game: Game) -> list[tuple[int, int]]:
        """Return module-aligned character spans across the full track width."""
        track_modules = game.track_modules
        if not track_modules:
            return []

        width = self.__track_width_chars
        total_length = sum(max(0.0, module.length) for module in track_modules)

        if total_length <= 0:
            step = width / len(track_modules)
            boundaries = [int(round(index * step)) for index in range(len(track_modules) + 1)]
        else:
            boundaries = [0]
            cumulative = 0.0
            for module in track_modules:
                cumulative += max(0.0, module.length)
                boundaries.append(int(round((cumulative / total_length) * width)))

        boundaries[0] = 0
        boundaries[-1] = width
        for index in range(1, len(boundaries)):
            if boundaries[index] < boundaries[index - 1]:
                boundaries[index] = boundaries[index - 1]

        spans: list[tuple[int, int]] = []
        for index in range(len(track_modules)):
            start = min(max(0, boundaries[index]), width - 1)
            end = min(max(start + 1, boundaries[index + 1]), width)
            spans.append((start, end))

        return spans

    @staticmethod
    def __lane_track_length(track_modules: list[TrackModule], lane: Lane) -> float:
        return sum(module.get_line_length_for_lane(lane) for module in track_modules)

    @staticmethod
    def __resolve_lane_module_position(
        track_modules: list[TrackModule],
        lane: Lane,
        position: float,
    ) -> tuple[int | None, float]:
        lane_length = sum(module.get_line_length_for_lane(lane) for module in track_modules)
        if lane_length <= 0:
            return None, 0.0

        normalized_position = position % lane_length if position >= 0 else 0.0
        cumulative = 0.0
        for module_index, module in enumerate(track_modules):
            line_length = module.get_line_length_for_lane(lane)
            if line_length <= 0:
                continue

            upper_bound = cumulative + line_length
            if normalized_position < upper_bound:
                return module_index, normalized_position - cumulative
            cumulative = upper_bound

        return None, normalized_position

    def __module_boundaries_for_lane(self, track_modules: list[TrackModule], lane: Lane) -> list[int]:
        lane_length = self.__lane_track_length(track_modules, lane)
        if lane_length <= 0:
            return []

        boundaries: list[int] = [0]
        running_length = 0.0
        for module in track_modules:
            line_length = module.get_line_length_for_lane(lane)
            if line_length <= 0:
                continue

            running_length += line_length
            boundary_idx = int((running_length / lane_length) * (self.__track_width_chars - 1))
            boundaries.append(boundary_idx)

        return boundaries
