from __future__ import annotations

from database import get_connection


def fetch_food_scenario_rows(log_id: int, user_id: int) -> list[dict]:
    """Loads existing food rows for What-if simulation using SELECT-only access."""
    conn = get_connection()
    if not conn:
        return []

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT *
            FROM (
                SELECT
                    fl.id,
                    'Aliment' AS entry_type,
                    fi.name AS label,
                    fl.quantity_g,
                    fi.calories_100g,
                    fi.protein_g,
                    fi.carbs_g,
                    fi.fats_g,
                    fl.meal_type,
                    fl.meal_time,
                    COALESCE(
                        CASE
                            WHEN fi.source = 'USDA' AND fi.source_type = 'SR Legacy' THEN 'USDA SR'
                            WHEN fi.source = 'USDA' AND fi.source_type = 'Foundation' THEN 'USDA Foundation'
                            WHEN fi.source = 'USDA' AND fi.source_type = 'Survey (FNDDS)' THEN 'USDA FNDDS'
                            WHEN fi.source IS NOT NULL AND fi.source_type IS NOT NULL THEN fi.source || ' ' || fi.source_type
                            WHEN fi.source IS NOT NULL THEN fi.source
                            ELSE NULL
                        END,
                        'MacroSense'
                    ) AS source_label
                FROM food_logs fl
                JOIN daily_logs dl ON dl.id = fl.log_id
                JOIN food_items fi ON fi.id = fl.food_id
                WHERE fl.log_id = %s
                  AND dl.user_id = %s
                  AND fl.food_id IS NOT NULL

                UNION ALL

                SELECT
                    fl.id,
                    'Masă personalizată' AS entry_type,
                    fl.snapshot_name AS label,
                    fl.quantity_g,
                    fl.snapshot_calories_100g AS calories_100g,
                    fl.snapshot_protein_100g AS protein_g,
                    fl.snapshot_carbs_100g AS carbs_g,
                    fl.snapshot_fats_100g AS fats_g,
                    fl.meal_type,
                    fl.meal_time,
                    'Snapshot masă' AS source_label
                FROM food_logs fl
                JOIN daily_logs dl ON dl.id = fl.log_id
                WHERE fl.log_id = %s
                  AND dl.user_id = %s
                  AND fl.custom_meal_id IS NOT NULL
            ) rows
            ORDER BY meal_time ASC NULLS LAST, id ASC
            """,
            (log_id, user_id, log_id, user_id),
        )
        return [
            {
                "scenario_id": f"real_food_{row[0]}",
                "entry_type": row[1],
                "label": row[2],
                "quantity_g": float(row[3]),
                "calories_100g": float(row[4] or 0),
                "protein_100g": float(row[5] or 0),
                "carbs_100g": float(row[6] or 0),
                "fats_100g": float(row[7] or 0),
                "meal_type": row[8],
                "meal_time": row[9],
                "source_label": row[10],
                "is_existing": True,
            }
            for row in cursor.fetchall()
        ]
    except Exception as exc:
        print(f"Error loading What-if food rows: {exc}")
        return []
    finally:
        if conn:
            conn.close()


def fetch_activity_scenario_rows(log_id: int, user_id: int) -> list[dict]:
    """Loads existing activity rows for What-if simulation using SELECT-only access."""
    conn = get_connection()
    if not conn:
        return []

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                al.id,
                a.name,
                a.category,
                al.duration_min,
                al.sets,
                al.reps,
                al.manual_calories_burned,
                a.met_multiplier,
                COALESCE(
                    CASE
                        WHEN a.source IS NOT NULL AND a.source_type IS NOT NULL THEN a.source || ' ' || a.source_type
                        WHEN a.source IS NOT NULL THEN a.source
                        ELSE NULL
                    END,
                    'MacroSense'
                ) AS source_label
            FROM activity_logs al
            JOIN daily_logs dl ON dl.id = al.log_id
            JOIN activities a ON a.id = al.activity_id
            WHERE al.log_id = %s
              AND dl.user_id = %s
            ORDER BY al.id ASC
            """,
            (log_id, user_id),
        )
        return [
            {
                "scenario_id": f"real_activity_{row[0]}",
                "label": row[1],
                "category": row[2],
                "duration_min": float(row[3]),
                "sets": int(row[4]) if row[4] is not None else None,
                "reps": int(row[5]) if row[5] is not None else None,
                "manual_calories_burned": float(row[6]) if row[6] is not None else None,
                "met": float(row[7]),
                "source_label": row[8],
                "is_existing": True,
            }
            for row in cursor.fetchall()
        ]
    except Exception as exc:
        print(f"Error loading What-if activity rows: {exc}")
        return []
    finally:
        if conn:
            conn.close()
