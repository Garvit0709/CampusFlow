
import { useMemo } from "react";
import "./BidholiWalkingDirections.css";

function distanceBetween(a, b) {
  const toRadians = (degrees) =>
    (degrees * Math.PI) / 180;

  const lat1 = toRadians(Number(a[0]));
  const lat2 = toRadians(Number(b[0]));
  const dLat = lat2 - lat1;
  const dLon = toRadians(
    Number(b[1]) - Number(a[1])
  );

  const value =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1) *
      Math.cos(lat2) *
      Math.sin(dLon / 2) ** 2;

  return (
    6371000 *
    2 *
    Math.asin(
      Math.sqrt(Math.min(1, Math.max(0, value)))
    )
  );
}

function createDirections(route) {
  const names = route?.path_names || [];
  const types = route?.path_node_types || [];
  const coordinates =
    route?.path_coordinates ||
    route?.coordinates ||
    [];

  if (!names.length) return [];

  const steps = [
    {
      title: `Start at ${names[0]}`,
      description:
        "Begin at your selected starting location.",
      type: "start",
    },
  ];

  for (let index = 1; index < names.length; index++) {
    const isLast = index === names.length - 1;

    if (isLast) {
      steps.push({
        title: `Arrive at ${names[index]}`,
        description:
          "You have reached your destination.",
        type: "destination",
      });

      continue;
    }

    const isJunction =
      types[index] === "junction";

    const previousPoint = coordinates[index - 1];
    const currentPoint = coordinates[index];

    const straightDistance =
      previousPoint && currentPoint
        ? Math.round(
            distanceBetween(
              previousPoint,
              currentPoint
            )
          )
        : null;

    const description = isJunction
      ? "Continue through this mapped pedestrian junction."
      : "Continue along the mapped pedestrian connection.";

    steps.push({
      title: isJunction
        ? `Pass ${names[index]}`
        : `Continue via ${names[index]}`,
      description:
        straightDistance === null
          ? description
          : `${description} Approx. ${straightDistance} m straight-line separation from the previous point.`,
      type: isJunction ? "junction" : "landmark",
    });
  }

  return steps;
}

export default function BidholiWalkingDirections({
  route,
}) {
  const steps = useMemo(
    () => createDirections(route),
    [route]
  );

  if (!route || steps.length === 0) {
    return null;
  }

  return (
    <section className="bidholi-directions">
      <div className="bidholi-directions-header">
        <div>
          <span className="bidholi-eyebrow">
            WALKING GUIDE
          </span>
          <h3>Step-by-Step Directions</h3>
        </div>

        <span className="bidholi-directions-count">
          {steps.length} steps
        </span>
      </div>

      <div className="bidholi-directions-summary">
        <div>
          <small>Estimated Distance</small>
          <strong>
            {route.estimated_distance_m} m
          </strong>
        </div>

        <div>
          <small>Walking Time</small>
          <strong>
            {route.estimated_time_min} min
          </strong>
        </div>
      </div>

      <div className="bidholi-directions-steps">
        {steps.map((step, index) => (
          <div
            key={`${index}-${step.title}`}
            className={
              `bidholi-direction-step ${step.type}`
            }
          >
            <span className="bidholi-step-number">
              {index + 1}
            </span>

            <div>
              <strong>{step.title}</strong>
              <p>{step.description}</p>
            </div>
          </div>
        ))}
      </div>

      {route.contains_stairs && (
        <p className="bidholi-directions-alert">
          This route includes stairs. Enable
          Avoid Stairs to request an alternative.
        </p>
      )}

      {route.contains_unverified_geometry && (
        <p className="bidholi-directions-note">
          Directions follow mapped buildings and
          junctions. Exact turns, crossings and
          walking distances have not been verified
          on the ground.
        </p>
      )}
    </section>
  );
}
