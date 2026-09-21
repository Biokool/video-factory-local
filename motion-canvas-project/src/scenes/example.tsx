import {makeScene2D, Circle, Line, Txt, Node, Layout} from '@motion-canvas/2d';
import {
  all, chain, waitFor, createRef, createSignal,
  Direction, Vector2d,
} from '@motion-canvas/core';

export default makeScene2D(function* (view) {
  // Background
  view.fill('#0a0a1a');

  // Title
  const title = createRef<Txt>();
  const subtitle = createRef<Txt>();

  view.add(
    <>
      <Txt
        ref={title}
        text="LECTURA DE MANO"
        fontSize={72}
        fontWeight={700}
        fill={'#ffffff'}
        y={-300}
        opacity={0}
      />
      <Txt
        ref={subtitle}
        text="La Línea de la Vida"
        fontSize={36}
        fontWeight={400}
        fill={'#b8a9d4'}
        y={-220}
        opacity={0}
      />
    </>
  );

  // Animate title
  yield* title().opacity(1, 0.5);
  yield* subtitle().opacity(1, 0.5);

  // Hand outline (simplified palm shape)
  const handPath = createRef<Line>();
  const palmPoints = [
    new Vector2d(-150, 200),
    new Vector2d(-200, 0),
    new Vector2d(-180, -100),
    new Vector2d(-150, -200),
    new Vector2d(-100, -300),
    new Vector2d(-50, -350),
    new Vector2d(0, -380),
    new Vector2d(50, -350),
    new Vector2d(100, -300),
    new Vector2d(150, -200),
    new Vector2d(180, -100),
    new Vector2d(200, 0),
    new Vector2d(150, 200),
  ];

  view.add(
    <Line
      ref={handPath}
      points={palmPoints}
      stroke={'#F5CBA7'}
      lineWidth={4}
      radius={20}
      fill={'#F5CBA7'}
      opacity={0}
      y={50}
    />
  );

  yield* handPath().opacity(1, 0.8);

  // Life line
  const lifeLine = createRef<Line>();
  const lifePoints = [
    new Vector2d(-80, -50),
    new Vector2d(-100, 50),
    new Vector2d(-90, 150),
    new Vector2d(-50, 200),
  ];

  view.add(
    <Line
      ref={lifeLine}
      points={lifePoints}
      stroke={'#00D4FF'}
      lineWidth={8}
      lineDash={[16, 8]}
      opacity={0}
      y={50}
    />
  );

  // Animate life line drawing
  yield* lifeLine().opacity(1, 0.3);
  yield* lifeLine().stroke('#00D4FF', 0);

  // Label
  const label = createRef<Txt>();
  view.add(
    <Txt
      ref={label}
      text="Línea de la Vida"
      fontSize={28}
      fill={'#00D4FF'}
      x={200}
      y={100}
      opacity={0}
    />
  );

  yield* label().opacity(1, 0.5);
  yield* waitFor(1);

  // Fade out
  yield* all(
    title().opacity(0, 0.5),
    subtitle().opacity(0, 0.5),
    handPath().opacity(0, 0.5),
    lifeLine().opacity(0, 0.5),
    label().opacity(0, 0.5),
  );
});
