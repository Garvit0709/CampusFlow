
import "./BidholiMobileToolbar.css";

const ITEMS = [
  {
    id: "bidholi-mobile-map",
    label: "Map",
    icon: "🗺️",
  },
  {
    id: "bidholi-mobile-routes",
    label: "Routes",
    icon: "🧭",
  },
  {
    id: "bidholi-mobile-directory",
    label: "Places",
    icon: "📍",
  },
  {
    id: "bidholi-mobile-editor",
    label: "Junctions",
    icon: "🛠️",
  },
];

export default function BidholiMobileToolbar() {
  function navigateTo(id) {
    const element = document.getElementById(id);

    if (!element) return;

    element.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  }

  return (
    <nav
      className="cf-mobile-toolbar"
      aria-label="Campus navigation shortcuts"
    >
      {ITEMS.map((item) => (
        <button
          key={item.id}
          type="button"
          onClick={() => navigateTo(item.id)}
          aria-label={`Go to ${item.label}`}
        >
          <span
            className="cf-mobile-toolbar-icon"
            aria-hidden="true"
          >
            {item.icon}
          </span>

          <span>{item.label}</span>
        </button>
      ))}
    </nav>
  );
}
