import re
from flask import Flask, request, jsonify

app = Flask(__name__)

def extract_parameters_from_text(text):
    """
    Извлекает параметры (масса, угол, скорость) из текста задачи
    с использованием регулярных выражений.
    """
    mass = None
    angle = None
    speed = None

    # Ищем массу (например, "массой 2 кг", "масса 5кг", "2 кг")
    # Поддерживает целые и дробные числа (с точкой или запятой)
    mass_match = re.search(r'(?:масс[аоый]\s*|m\s*=\s*)(\d+[\.,]?\d*)\s*(?:кг|килограмм)?', text, re.IGNORECASE)
    if not mass_match: # Попробуем найти просто число перед "кг"
        mass_match = re.search(r'(\d+[\.,]?\d*)\s*кг', text, re.IGNORECASE)
    if mass_match:
        try:
            mass_str = mass_match.group(1).replace(',', '.')
            mass = float(mass_str)
        except ValueError:
            pass # Ошибка конвертации, mass останется None

    # Ищем угол (например, "углом 30 градусов", "угол 45°", "под углом 20.5 гр")
    angle_match = re.search(r'(?:угл[оаыом]\s*(?:к горизонту)?\s*|alpha\s*=\s*|угол\s+наклона\s+составляет\s*)(\d+[\.,]?\d*)\s*(?:градус[ов]?)?', text, re.IGNORECASE)
    if not angle_match: # Попробуем найти число перед "°" или "град"
         angle_match = re.search(r'(\d+[\.,]?\d*)\s*(?:°|град)', text, re.IGNORECASE)
    if angle_match:
        try:
            angle_str = angle_match.group(1).replace(',', '.')
            angle = float(angle_str)
        except ValueError:
            pass

    # Ищем скорость (например, "скоростью 10 м/с", "скорость 20м/с", "v = 5 мс")
    speed_match = re.search(r'(?:скорость[юью]?\s*|v\s*=\s*)(\d+[\.,]?\d*)\s*(?:м/с|мс\-1|м сек|метров в секунду)?', text, re.IGNORECASE)
    if speed_match:
        try:
            speed_str = speed_match.group(1).replace(',', '.')
            speed = float(speed_str)
        except ValueError:
            pass

    return {"mass": mass, "angle": angle, "speed": speed}

@app.route('/parse_task', methods=['POST'])
def parse_task():
    if request.method == 'POST':
        data = request.get_json()
        task_description = data.get('task_description', '')

        if not task_description:
            return jsonify({"error": "Описание задачи отсутствует"}), 400

        parameters = extract_parameters_from_text(task_description)
        parameters["original_text"] = task_description
        parameters["message"] = "Параметры извлечены"

        # Для отладки выведем в консоль сервера
        print(f"Получен текст: {task_description}")
        print(f"Извлеченные параметры: {parameters}")

        return jsonify(parameters)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
