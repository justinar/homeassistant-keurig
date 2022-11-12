from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from . import KeurigCoordinator
from homeassistant.core import HomeAssistant, callback
from .const import DOMAIN, MANUFACTURER
from homeassistant.components.sensor import SensorEntity


async def async_setup_entry(hass: HomeAssistant, config, add_entities):
    coordinator: KeurigCoordinator = hass.data[DOMAIN][config.entry_id]

    devices = await coordinator.get_devices()

    entities = []
    for brewer in devices:
        await brewer.async_update()
        entities.append(
            KeurigSensorEntity(
                hass=hass,
                name="Pod Status",
                device=brewer,
                coordinator=coordinator,
                device_type="pod_status",
            )
        )
        entities.append(
            KeurigSensorEntity(
                hass=hass,
                name="Brewer Status",
                device=brewer,
                coordinator=coordinator,
                device_type="brewer_status",
            )
        )

    add_entities(entities)


class KeurigSensorEntity(SensorEntity, CoordinatorEntity):
    def __init__(self, hass, name, device, coordinator, device_type):
        self._hass = hass
        self._device = device
        self._coordinator = coordinator
        self._device_type = device_type

        self._attr_name = name
        # self._attr_device_class = device_class
        self._attr_has_entity_name = True

        self._attr_unique_id = device.id + "_" + device_type
        self._attr_icon = "mdi:coffee-maker"

        device.register_callback(self._update_data)

        if self._device_type == "pod_status":
            self._attr_native_value = self.__pod_status_string(self._device.pod_status)
        elif self._device_type == "brewer_status":
            self._attr_native_value = self.__brewer_status_string(
                self._device.brewer_status, self._device.errors
            )

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device.id)},
            manufacturer=MANUFACTURER,
            name=device.name,
            model=device.model,
            sw_version=device.sw_version,
        )

        super().__init__(coordinator)

    @callback
    def _update_data(self, args):
        if self._device_type == "pod_status":
            self._attr_native_value = self.__pod_status_string(self._device.pod_status)
        elif self._device_type == "brewer_status":
            self._attr_native_value = self.__brewer_status_string(
                self._device.brewer_status, self._device.errors
            )
        self.schedule_update_ha_state(False)

    def __pod_status_string(self, value: str):
        if value == "EMPTY":
            return "empty"
        elif value == "PUNCHED":
            return "used"
        elif value == "POD":
            return "present"
        else:
            return value

    def __brewer_status_string(self, value: str, errors: list):
        if value == "BREW_READY":
            return "ready"
        elif value == "BREW_LOCKED":
            if "ADD_WATER" in errors or "BREW_INSUFFICIENT_WATER" in errors:
                return "no water"
            elif "PM_NOT_CYCLED" in errors:
                return "pod not removed"
            elif "PM_NOT_READY" in errors:
                return "lid open"
            else:
                return errors if errors is not None else value
        elif value == "BREW_CANCELING":
            return "canceling"
        elif value == "BREW_IN_PROGRESS":
            return "brewing"
        elif value == "BREW_SUCCESSFUL":
            return "complete"
        else:
            return value
