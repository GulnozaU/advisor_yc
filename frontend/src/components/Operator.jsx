import { useEffect, useRef } from "react";
import { Rive } from "@rive-app/canvas";

// Orange Rive character; parent sets --v (0..1 voice volume) on an ancestor for the talking mouth.
export const Operator = ({ live = false, speaking = false, size = 150, testId = "rive-operator" }) => {
  const canvasRef = useRef(null);
  const riveRef = useRef(null);

  useEffect(() => {
    const r = new Rive({
      src: "/orange-operator.riv",
      canvas: canvasRef.current,
      autoplay: true,
      onLoad: () => {
        r.resizeDrawingSurfaceToCanvas();
        if (r.stateMachineNames.length) r.play(r.stateMachineNames[0]);
      },
    });
    riveRef.current = r;
    return () => r.cleanup();
  }, []);

  useEffect(() => {
    const input = riveRef.current?.stateMachineInputs("State Machine 1")?.find((i) => i.name === "istracking");
    if (input) input.value = live;
  }, [live]);

  return (
    <div className={`op-wrap ${live ? "is-live" : ""} ${speaking ? "is-speaking" : ""}`} style={{ "--op": `${size}px` }} data-testid={`${testId}-wrap`}>
      <div className="op-ring op-ring-2" />
      <div className="op-ring" />
      <div className="op-orb">
        <div className="op-face">
          <canvas ref={canvasRef} width="300" height="300" data-testid={testId} />
          <div className="op-mouth" data-testid={`${testId}-mouth`} />
        </div>
      </div>
    </div>
  );
};
