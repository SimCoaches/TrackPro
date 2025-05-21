from trackpro.race_coach import ui

# Check if the methods are now in the class
print(f'RaceCoachWidget has load_throttle_data: {hasattr(ui.RaceCoachWidget, "load_throttle_data")}')
print(f'RaceCoachWidget has _on_telemetry_load_finished: {hasattr(ui.RaceCoachWidget, "_on_telemetry_load_finished")}')
print(f'RaceCoachWidget has _on_telemetry_load_error: {hasattr(ui.RaceCoachWidget, "_on_telemetry_load_error")}')
print(f'RaceCoachWidget has _cleanup_telemetry_load_references: {hasattr(ui.RaceCoachWidget, "_cleanup_telemetry_load_references")}')
print(f'RaceCoachWidget has load_all_laps_for_session: {hasattr(ui.RaceCoachWidget, "load_all_laps_for_session")}') 