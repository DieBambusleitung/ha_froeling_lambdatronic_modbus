from homeassistant.components.switch import SwitchEntity
from pymodbus.client import ModbusTcpClient
import logging
from datetime import timedelta
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.translation import async_get_translations
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    data = config_entry.data
    translations = await async_get_translations(hass, hass.config.language, "entity")

    def create_switches():
        switches = []
        # Create HK1-Freigabe Switch
        switches.extend([
            FroelingSwitch(hass, translations, data, "HK1_Freigabe", 48029)
        ])

        return switches

    switches = create_switches()
    async_add_entities(switches)

    update_interval = timedelta(seconds=data.get('update_interval', 60))
    for switch in switches:
        async_track_time_interval(hass, switch.async_update, update_interval)


class FroelingSwitch(SwitchEntity):
    def __init__(self, hass, translations, data, entity_id, register):
        self._hass = hass
        self._translations = translations
        self._host = data['host']
        self._port = data['port']
        self._device_name = data['name']
        self._entity_id = entity_id
        self._register = register
        self._device_class = device_class="switch"
        self._is_on = None
    
    @property
    def unique_id(self):
        return f"{self._device_name}_{self._entity_id}"

    @property
    def name(self):
        translated_name = self._translations.get(f"component.froeling_lambdatronic_modbus.entity.number.{self._entity_id}.name", self._entity_id)
        return f"{self._device_name} {translated_name}"

    @property
    def device_class(self):
        return self._device_class

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._device_name)},
            "name": self._device_name,
            "manufacturer": "Froeling",
            "model": "Lambdatronic Modbus",
            "sw_version": "1.0",
        }

    async def async_turn_on(self, **kwargs):
        client = ModbusTcpClient(self._host, port=self._port)
        if client.connect():
            try:
                client.write_register(self._register - 40001, count=1, device_id=2)
                self._is_on = True
            except Exception as e:
                _LOGGER.error("Exception during Modbus communication: %s", e)
                self._is_on = None
            finally:
                client.close()

    async def async_turn_off(self, **kwargs):
        client = ModbusTcpClient(self._host, port=self._port)
        if client.connect():
            try:
                client.write_register(self._register - 40001, count=0, device_id=2)
                self._is_on = False
            except Exception as e:
                _LOGGER.error("Exception during Modbus communication: %s", e)
                self._is_on = None
            finally:
                client.close()

    async def async_toggle(self, **kwargs):
        client = ModbusTcpClient(self._host, port=self._port)
        if client.connect():
            try:
                client.write_register(self._register - 40001, count=f"{1 if wert else 0}", device_id=2)
                self._is_on = not self._is_on
            except Exception as e:
                _LOGGER.error("Exception during Modbus communication: %s", e)
                self._is_on = None
            finally:
                client.close()

    async def async_update(self, _=None):
        client = ModbusTcpClient(self._host, port=self._port)
        if client.connect():
            try:
                result = client.read_holding_registers(self._register - 40001, count=1, device_id=2)
                if result.isError():
                    _LOGGER.error("Error reading Modbus holding register %s", self._register - 40001)
                    self._is_on = None
                else:
                    raw_value = result.registers[0]
                    self._is_on = f"{bool(raw_value)}"
                    _LOGGER.debug("processed Modbus holding register %s: raw_value=%s, _value=%s", self._register - 40001, raw_value, self._is_on)
            except Exception as e:
                _LOGGER.error("Exception during Modbus communication: %s", e)
            finally:
                client.close()