
/*
 * CampusFlow Phase 9.6
 * UPES Bidholi Photo and Location Details
 *
 * Photos should be stored in:
 * frontend/public/locations/bidholi/
 */

const PHOTO_BASE = "/locations/bidholi";

const photoFiles = {
  "9th block": ["9th-block.jpg"],
  "11th block": ["11th-block.jpg"],
  "boys hostel": ["boys-hostel.jpg"],
  "laboratory block": ["laboratory-block.jpg"],
  "tulip cafe": ["tulip-cafe.jpg"],
  "gandhi chowk": ["gandhi-chowk.jpg"],
  "7th block": ["7th-block.jpg"],
  "6th block": ["6th-block.jpg"],
  "library": ["library.jpg"],
  "upes museum": ["upes-museum.jpg"],
  "ground": ["ground.jpg"],
  "team orange": ["team-orange.jpg"],
  "food court 2": ["food-court-2.jpg"],
  "mac": ["mac.jpg"],
  "gym": ["gym.jpg"],
  "enrollment office": ["enrollment-office.jpg"],
  "1st block": ["1st-block.jpg"],
  "hubble": ["hubble.jpg"],
  "main gate": ["main-gate.jpg"],
  "food court": ["food-court.jpg"],
  "2nd block": ["2nd-block.jpg"],
  "3rd block": ["3rd-block.jpg"],
  "5th block": ["5th-block.jpg"],
  "4th block": ["4th-block.jpg"],
  "cafe": ["cafe.jpg"],
  "cafe frisco": ["cafe-frisco.jpg"],
  "girls hostel": ["girls-hostel.jpg"],
  "management building": ["management-building.jpg"],
  "management buildiung": ["management-building.jpg"],
  "it block": ["it-block.jpg"],
  "10th block": ["10th-block.jpg"],
};

const locationDetails = {
  "main gate": {
    description: "Main entrance area of UPES Bidholi.",
    facilities: ["Campus entrance"],
  },

  "library": {
    description: "UPES Bidholi campus library.",
    facilities: ["Library", "Study area"],
  },

  "gandhi chowk": {
    description: "Campus landmark and pedestrian junction.",
    facilities: ["Walking junction"],
  },

  "it block": {
    description: "IT Block at UPES Bidholi.",
    facilities: ["Academic facilities"],
  },

  "food court": {
    description: "Campus dining area.",
    facilities: ["Food and beverages"],
  },
};

export function normalizeLocationName(name = "") {
  return String(name)
    .trim()
    .toLowerCase()
    .replace(/café/g, "cafe")
    .replace(/\s+/g, " ");
}

export function getLocationPhotos(location) {
  const normalizedName = normalizeLocationName(
    location.original_name || location.name
  );

  const files = photoFiles[normalizedName] || [];

  return files.map((filename) => ({
    src: `${PHOTO_BASE}/${filename}`,
    alt: `${location.name} at UPES Bidholi`,
  }));
}

export function getLocationDetails(location) {
  const normalizedName = normalizeLocationName(
    location.original_name || location.name
  );

  return (
    locationDetails[normalizedName] || {
      description: `${location.name} at UPES Bidholi Campus.`,
      facilities: [],
    }
  );
}
