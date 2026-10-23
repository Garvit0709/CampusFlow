
export const campusLocations = [
  {
    id: "gate",
    name: "Main Gate",
    position: [28.6139, 77.2090],
  },
  {
    id: "library",
    name: "Central Library",
    position: [28.6147, 77.2097],
  },
  {
    id: "blockA",
    name: "Academic Block A",
    position: [28.6154, 77.2105],
  },
  {
    id: "cafeteria",
    name: "Cafeteria",
    position: [28.6135, 77.2102],
  },
  {
    id: "hostel",
    name: "Student Hostel",
    position: [28.6140, 77.2113],
  },
  {
    id: "sports",
    name: "Sports Complex",
    position: [28.6150, 77.2120],
  },
];

export const campusEdges = [
  { from: "gate", to: "library", distance: 120 },
  { from: "gate", to: "cafeteria", distance: 150 },
  { from: "library", to: "blockA", distance: 130 },
  { from: "library", to: "cafeteria", distance: 180 },
  { from: "cafeteria", to: "hostel", distance: 140 },
  { from: "blockA", to: "hostel", distance: 200 },
  { from: "blockA", to: "sports", distance: 160 },
  { from: "hostel", to: "sports", distance: 170 },
];
