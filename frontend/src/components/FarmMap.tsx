import { divIcon } from 'leaflet';
import { Circle, MapContainer, Marker, Polyline, TileLayer, Tooltip } from 'react-leaflet';
import type { Geofence, LiveAnimal, TrackPoint } from '../types/models';

const SPECIES_COLOR: Record<string, string> = {
  cattle: '#8d6e63',
  buffalo: '#455a64',
  goat: '#ef6c00',
  sheep: '#a1887f',
  pig: '#ec407a',
  poultry: '#fbc02d',
};

function animalIcon(species: string, breach: boolean) {
  const color = SPECIES_COLOR[species] ?? '#003527';
  return divIcon({
    className: '',
    iconSize: [18, 18],
    iconAnchor: [9, 9],
    html: `<span style="
      display:block;width:${breach ? 20 : 14}px;height:${breach ? 20 : 14}px;margin:0;border-radius:9999px;
      background:${color};border:2.5px solid ${breach ? '#dc362e' : '#ffffff'};
      box-shadow:0 0 0 ${breach ? 6 : 2}px ${breach ? 'rgba(220,54,46,.25)' : 'rgba(0,0,0,.15)'};
    "></span>`,
  });
}

const centerIcon = divIcon({
  className: '',
  iconSize: [22, 22],
  iconAnchor: [11, 11],
  html: `<span style="display:block;width:12px;height:12px;margin:5px;border-radius:9999px;
         background:#003527;border:2px solid #fff;box-shadow:0 0 0 2px rgba(0,53,39,.35);"></span>`,
});

export default function FarmMap({
  fence,
  animals,
  center,
  radiusM,
  onCenterMoved,
  onSelect,
  selectedId,
  history,
}: {
  fence: Geofence;
  animals: LiveAnimal[];
  center: [number, number];
  radiusM: number;
  onCenterMoved: (lat: number, lng: number) => void;
  onSelect: (animalId: number) => void;
  selectedId?: number | null;
  history?: TrackPoint[];
}) {
  return (
    <div className="relative z-0 overflow-hidden rounded-2xl">
      <MapContainer
        center={center}
        zoom={15}
        scrollWheelZoom
        className="h-[420px] w-full"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {/* farm boundary */}
        <Circle
          center={[fence.center_lat, fence.center_lng]}
          radius={radiusM}
          pathOptions={{ color: '#003527', weight: 2, fillColor: '#003527', fillOpacity: 0.06 }}
        />
        <Marker
          position={[fence.center_lat, fence.center_lng]}
          icon={centerIcon}
          draggable
          eventHandlers={{
            dragend: (e) => {
              const p = e.target.getLatLng();
              onCenterMoved(p.lat, p.lng);
            },
          }}
          title="Farm centre — drag to move the boundary"
        />

        {/* selected animal trail */}
        {history && history.length > 1 && (
          <Polyline
            positions={history.map((p) => [p.lat, p.lng])}
            pathOptions={{ color: '#00796b', weight: 2.5, dashArray: '4 6', opacity: 0.8 }}
          />
        )}

        {/* animals */}
        {animals.map((a) => (
          <Marker
            key={a.animal_id}
            position={[a.lat, a.lng]}
            icon={animalIcon(a.species, a.breach)}
            eventHandlers={{ click: () => onSelect(a.animal_id) }}
          >
            <Tooltip direction="top" offset={[0, -10]}>
              <b>{a.tag_id}</b> · {a.species}
              <br />
              {a.breach
                ? `⚠ outside boundary by ${Math.round(a.distance_from_center_m - fence.radius_m)} m`
                : `${Math.round(a.distance_from_center_m)} m from centre`}
              <br />
              <span style={{ fontSize: 10 }}>{a.recorded_at_display}</span>
            </Tooltip>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
}
