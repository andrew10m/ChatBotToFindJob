// Глобальные переменные для хранения текущих параметров для p5.js
let currentVizParams = {
    mass: null,
    angle: null,
    speed: null,
    taskType: 'none' // 'inclined_plane', 'projectile_motion', 'none'
};

// p5.js экземпляр
let sketch = function(p) {
    let canvasContainer;

    p.setup = function() {
        canvasContainer = document.getElementById('canvas-container');
        let canvas = p.createCanvas(canvasContainer.offsetWidth, canvasContainer.offsetHeight);
        canvas.parent('canvas-container');
        p.background(230);
        p.textAlign(p.CENTER, p.CENTER);
        p.textSize(16);
        p.text("Ожидание параметров для визуализации...", p.width / 2, p.height / 2);
    };

    p.draw = function() {
        p.background(230); // Очищаем холст на каждом кадре

        if (currentVizParams.taskType === 'inclined_plane') {
            drawInclinedPlane(p, currentVizParams.angle);
        } else if (currentVizParams.taskType === 'projectile_motion') {
            drawProjectileMotion(p, currentVizParams.angle, currentVizParams.speed);
        } else {
            p.textAlign(p.CENTER, p.CENTER);
            p.textSize(16);
            p.fill(0);
            p.text("Выберите задачу или введите параметры", p.width / 2, p.height / 2);
        }
    };

    p.windowResized = function() {
        p.resizeCanvas(canvasContainer.offsetWidth, canvasContainer.offsetHeight);
    };
};

// Запускаем p5.js
new p5(sketch);

function updateVisualization(params) {
    console.log("Обновление визуализации с параметрами:", params);
    currentVizParams.mass = params.mass;
    currentVizParams.angle = params.angle;
    currentVizParams.speed = params.speed;

    // Простое определение типа задачи для MVP
    if (params.angle !== null && params.mass !== null && params.speed === null) { // Пример: брусок на наклонной плоскости
        currentVizParams.taskType = 'inclined_plane';
    } else if (params.angle !== null && params.speed !== null) { // Пример: тело брошено под углом
        currentVizParams.taskType = 'projectile_motion';
    } else if (params.angle !== null) { // Если только угол, по умолчанию наклонная плоскость
         currentVizParams.taskType = 'inclined_plane';
    }
    else {
        currentVizParams.taskType = 'none';
    }
    // Перерисовка p5.js не нужна явно, так как draw() вызывается в цикле
}


function drawInclinedPlane(p, angleDegrees) {
    if (angleDegrees === null || angleDegrees < 0 || angleDegrees >= 90) {
        p.text("Некорректный угол для наклонной плоскости.", p.width / 2, p.height / 2);
        return;
    }

    let angleRadians = p.radians(angleDegrees);

    let planeBaseWidth = p.width * 0.6;
    let planeHeight = planeBaseWidth * p.tan(angleRadians);

    let startX = p.width * 0.2;
    let startY = p.height * 0.8;

    if (startY - planeHeight < p.height * 0.1) { // Если плоскость слишком высокая
        planeHeight = startY - p.height * 0.1;
        planeBaseWidth = planeHeight / p.tan(angleRadians);
        if (planeBaseWidth > p.width * 0.8) {
             planeBaseWidth = p.width * 0.8;
             planeHeight = planeBaseWidth * p.tan(angleRadians);
             startX = (p.width - planeBaseWidth) / 2;
        }
    }


    p.stroke(0);
    p.fill(200);

    // Рисуем треугольник наклонной плоскости
    p.beginShape();
    p.vertex(startX, startY); // Нижний левый угол
    p.vertex(startX + planeBaseWidth, startY); // Нижний правый угол
    p.vertex(startX, startY - planeHeight); // Верхний левый угол (гипотенуза)
    p.endShape(p.CLOSE);

    // Рисуем "землю"
    p.line(startX - 20, startY, startX + planeBaseWidth + 20, startY);

    // Рисуем брусок на плоскости (просто прямоугольник)
    if (currentVizParams.mass !== null) {
        let boxSize = 30;
        let boxX = startX + planeBaseWidth * 0.3; // Положение бруска на плоскости
        let boxYOnPlane = startY - (planeBaseWidth * 0.3) * p.tan(angleRadians);

        p.push(); // Сохраняем текущую систему координат
        p.translate(boxX, boxYOnPlane); // Перемещаем начало координат к точке на гипотенузе
        p.rotate(-angleRadians); // Поворачиваем систему координат параллельно плоскости

        p.fill(100, 100, 250);
        p.rect(-boxSize / 2, -boxSize, boxSize, boxSize); // Рисуем брусок относительно нового начала координат
        p.pop(); // Восстанавливаем систему координат
    }

    // Отображаем угол
    p.fill(0);
    p.textSize(14);
    p.textAlign(p.LEFT, p.BOTTOM);
    p.text(`Угол: ${angleDegrees.toFixed(1)}°`, startX + 10, startY - 5);

    // Рисуем силы, если есть масса и угол
    if (currentVizParams.mass !== null && angleDegrees !== null) {
        let g = 9.81;
        let mass = currentVizParams.mass;

        // Центр масс бруска в глобальных координатах
        let boxSize = 30;
        let boxCenterXGlobal = startX + planeBaseWidth * 0.3;
        let boxCenterYGlobal = startY - (planeBaseWidth * 0.3) * p.tan(angleRadians) - boxSize / 2 * p.cos(angleRadians) + boxSize / 2 * p.sin(angleRadians) * p.tan(angleRadians);
         // Коррекция для центра масс, если брусок повернут.
        // Более простой вариант: центр повернутого прямоугольника.
        // Координаты центра бруска относительно его левого нижнего угла (когда он еще не повернут)
        let rectCenterX_local = 0;
        let rectCenterY_local = -boxSize/2;

        // Преобразование локальных координат центра в глобальные с учетом поворота и сдвига
        let translatedBoxOriginX = startX + planeBaseWidth * 0.3;
        let translatedBoxOriginY = startY - (planeBaseWidth * 0.3) * p.tan(angleRadians);

        let cosA = p.cos(-angleRadians);
        let sinA = p.sin(-angleRadians);

        // Поворачиваем локальные координаты центра
        let rotatedRectCenterX = rectCenterX_local * cosA - rectCenterY_local * sinA;
        let rotatedRectCenterY = rectCenterX_local * sinA + rectCenterY_local * cosA;

        // Добавляем смещение, чтобы получить глобальные координаты центра
        boxCenterXGlobal = translatedBoxOriginX + rotatedRectCenterX;
        boxCenterYGlobal = translatedBoxOriginY + rotatedRectCenterY;


        let Fg = mass * g; // Сила тяжести
        let N = mass * g * p.cos(angleRadians); // Сила нормальной реакции
        // let Ffriction = mass * g * p.sin(angleRadians); // Сила трения скольжения (если движется равномерно или на грани)

        let vectorScale = 2; // Масштаб для векторов сил

        p.push();
        p.translate(boxCenterXGlobal, boxCenterYGlobal);

        // Сила тяжести (Fg) - всегда вертикально вниз
        p.stroke(255, 0, 0); // Красный
        p.line(0, 0, 0, Fg * vectorScale);
        p.fill(255, 0, 0);
        p.text("mg", 5, Fg * vectorScale / 2);

        // Сила нормальной реакции (N) - перпендикулярно плоскости
        p.stroke(0, 0, 255); // Синий
        p.rotate(-angleRadians); // Поворачиваем систему координат как плоскость
        p.line(0, 0, 0, -N * vectorScale);
        p.text("N", 5, -N * vectorScale / 2);

        // Составляющая силы тяжести, параллельная плоскости (mg_x)
        let mg_x = mass * g * p.sin(angleRadians);
        p.stroke(0, 150, 0); // Зеленый
        p.line(0,0, mg_x * vectorScale, 0);
        p.text("mg_x", mg_x*vectorScale/2, -5);

        // Составляющая силы тяжести, перпендикулярная плоскости (mg_y)
        let mg_y = mass * g * p.cos(angleRadians); // такая же как N по модулю
        p.stroke(200, 100, 0); // Оранжевый
        // Рисуем ее из той же точки, что и mg_x, но вдоль "новой" оси Y
        // Чтобы она была сонаправлена N (но из центра масс), ее нужно рисовать "вверх" в повернутой системе
        // Однако, ее обычно рисуют как компоненту mg, так что лучше из 0,0 в повернутой системе, но "вниз"
        // p.line(0,0, 0, mg_y * vectorScale); // Это будет вдоль N, но неверно
        // Вернемся в неповернутую систему для mg_y, но с началом в центре
        p.pop(); // Возвращаем изначальные координаты (до p.translate(boxCenterXGlobal, boxCenterYGlobal))
        p.push();
        p.translate(boxCenterXGlobal, boxCenterYGlobal);
        p.stroke(200,100,0);
        // mg_y направлена противоположно N, но вдоль той же линии действия
        // Рисуем из центра масс перпендикулярно плоскости "вниз"
        p.line(0,0, N * vectorScale * p.sin(angleRadians) , N * vectorScale * p.cos(angleRadians));
        p.text("mg_y", N * vectorScale * p.sin(angleRadians)/2 + 5 , (N * vectorScale * p.cos(angleRadians))/2);


        p.pop();
    }
}

function drawProjectileMotion(p, angleDegrees, initialSpeed) {
    if (angleDegrees === null || initialSpeed === null || angleDegrees < 0 || angleDegrees > 90 || initialSpeed <=0) {
        p.text("Некорректные параметры для движения снаряда.", p.width / 2, p.height / 2);
        return;
    }

    let angleRadians = p.radians(angleDegrees);
    let g = 9.81; // Ускорение свободного падения

    let v0x = initialSpeed * p.cos(angleRadians);
    let v0y = initialSpeed * p.sin(angleRadians);

    // Время полета до максимальной высоты (когда Vy = 0): t_peak = v0y / g
    // Общее время полета: T = 2 * t_peak = 2 * v0y / g
    let flightTime = (2 * v0y) / g;
    // Максимальная дальность: R = v0x * T
    let range = v0x * flightTime;
    // Максимальная высота: H = v0y^2 / (2g)
    let maxHeight = (v0y * v0y) / (2 * g);

    let scaleX = (p.width * 0.8) / range;
    let scaleY = (p.height * 0.6) / maxHeight;
    let scale = p.min(scaleX, scaleY); // Выбираем меньший масштаб, чтобы все влезло

    if (range === 0 || maxHeight === 0) scale = 10; // Запасной вариант, если что-то нулевое

    let startX = p.width * 0.1;
    let startY = p.height * 0.8; // Начало координат для траектории (земля)

    p.stroke(0);
    p.fill(150, 150, 250);

    // Рисуем траекторию
    p.noFill();
    p.beginShape();
    for (let t = 0; t <= flightTime; t += flightTime / 100) {
        let x = v0x * t;
        let y = v0y * t - 0.5 * g * t * t;
        p.vertex(startX + x * scale, startY - y * scale);
    }
    // Добавляем последнюю точку на земле
    p.vertex(startX + range * scale, startY);
    p.endShape();

    // Рисуем "землю"
    p.line(startX - 20, startY, startX + range * scale + 20, startY);

    // Рисуем начальный вектор скорости (просто линия)
    p.stroke(255,0,0);
    p.line(startX, startY, startX + v0x*scale*0.2, startY - v0y*scale*0.2); // Укороченный для наглядности
    p.stroke(0);

    // Отображаем параметры
    p.fill(0);
    p.textSize(14);
    p.textAlign(p.LEFT, p.BOTTOM);
    p.text(`Угол: ${angleDegrees.toFixed(1)}°`, startX, startY + 20);
    p.text(`Скорость: ${initialSpeed.toFixed(1)} м/с`, startX, startY + 40);
    p.text(`Дальность: ${range.toFixed(1)} м`, startX + range * scale / 2, startY + 20);
    p.text(`Высота: ${maxHeight.toFixed(1)} м`, startX + (v0x * (flightTime/2)) * scale + 5, startY - maxHeight*scale - 5);
}


document.addEventListener('DOMContentLoaded', () => {
    const taskInput = document.getElementById('task-input');
    const submitButton = document.getElementById('submit-task');
    const massInput = document.getElementById('mass');
    const angleInput = document.getElementById('angle');
    const speedInput = document.getElementById('speed');

    submitButton.addEventListener('click', async () => {
        const taskDescription = taskInput.value;
        if (!taskDescription) {
            alert('Пожалуйста, введите описание задачи.');
            return;
        }

        try {
            const response = await fetch('/parse_task', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ task_description: taskDescription }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `Ошибка сервера: ${response.status}`);
            }

            const params = await response.json();

            console.log("Получены параметры от бэкенда:", params);

            massInput.value = params.mass !== null ? params.mass : '';
            angleInput.value = params.angle !== null ? params.angle : '';
            speedInput.value = params.speed !== null ? params.speed : '';

            updateVisualization(params);

        } catch (error) {
            console.error('Ошибка при обработке задачи:', error);
            alert(`Произошла ошибка: ${error.message}`);
        }
    });

    function handleManualParamChange() {
        const params = {
            mass: massInput.value !== '' ? parseFloat(massInput.value) : null,
            angle: angleInput.value !== '' ? parseFloat(angleInput.value) : null,
            speed: speedInput.value !== '' ? parseFloat(speedInput.value) : null,
        };
        updateVisualization(params);
        console.log("Параметры изменены вручную, визуализация обновлена:", params);
    }

    massInput.addEventListener('input', handleManualParamChange);
    angleInput.addEventListener('input', handleManualParamChange);
    speedInput.addEventListener('input', handleManualParamChange);
});
