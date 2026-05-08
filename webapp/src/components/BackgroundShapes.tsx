/** Анимированный фон: 10 полупрозрачных белых фигур всплывают снизу
 * вверх, вращаясь и превращаясь из квадратов в круги. Pointer-events
 * выключены — фон не мешает интерактиву.
 *
 * Inspired by mohaiman/pen/MQqMyo. Адаптировано под тёмную тему
 * (фон чёрный/тёмно-синий, фигуры — белые с низкой непрозрачностью). */
export function BackgroundShapes() {
  return (
    <ul className="bg-shapes" aria-hidden="true">
      <li />
      <li />
      <li />
      <li />
      <li />
      <li />
      <li />
      <li />
      <li />
      <li />
    </ul>
  );
}
