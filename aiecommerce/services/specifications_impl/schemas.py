from typing import Literal, Optional, Union

from pydantic import BaseModel, Field


# --- Base Components ---
class BaseProductSpecs(BaseModel):
    manufacturer: Optional[str] = Field(None, description="The brand, e.g., Samsung, Dell, Asus, Apple, Epson")
    model_name: Optional[str] = Field(None, description="The specific model identifier (e.g., Galaxy S24, MacBook Pro, PRO Q670M-C-CSM)")
    part_number: Optional[str] = Field(None, description="The SKU, MPN, or specific part number if found")
    color: Optional[str] = Field(None, description="Product color")


# --- 1. Computers & Laptops ---
class NotebookSpecs(BaseProductSpecs):
    category_type: Literal["NOTEBOOK"] = "NOTEBOOK"
    cpu: Optional[str] = Field(None, description="Processor, e.g., M2, i7-13700H")
    ram: Optional[str] = Field(None, description="RAM capacity, e.g., 16GB")
    storage: Optional[str] = Field(None, description="Storage, e.g., 256GB SSD")
    screen_size: Optional[str] = Field(None, description="Screen size, e.g., 13.6 Inch")
    os: Optional[str] = Field(None, description="Operating System, e.g., MacOS")


class DesktopSpecs(BaseProductSpecs):
    """Covers Desktops, AIO, MiniPC, Barebones, Servers"""

    category_type: Literal["COMPUTADORES DESKTOP, AIO, MINIPC", "SERVIDORES"] = "COMPUTADORES DESKTOP, AIO, MINIPC"
    type: Optional[str] = Field(None, description="Tower, AIO, Mini PC, Server, Barebone")
    cpu: Optional[str] = Field(None, description="Processor model")
    ram: Optional[str] = Field(None, description="RAM capacity")
    storage: Optional[str] = Field(None, description="Storage capacity")
    form_factor: Optional[str] = Field(None, description="e.g., Rackmount (for servers), Tiny, SFF")


# --- 2. Core Components ---
class ProcessorSpecs(BaseProductSpecs):
    category_type: Literal["PROCESADORES"] = "PROCESADORES"
    socket: Optional[str] = Field(None, description="e.g., AM4, LGA1700")
    generation: Optional[str] = Field(None, description="e.g., Ryzen 5, i9 13th Gen")
    cores: Optional[str] = Field(None, description="Core/Thread count, e.g., 4 Core 8 Hilos")
    clock_speed: Optional[str] = Field(None, description="e.g., 3.7GHz")
    integrated_graphics: Optional[str] = Field(None, description="e.g., Radeon Vega 11")
    tdp: Optional[str] = Field(None, description="Thermal Design Power, e.g., 65W")


class MotherboardSpecs(BaseProductSpecs):
    category_type: Literal["MOTHER BOARDS"] = "MOTHER BOARDS"
    socket: Optional[str] = Field(None, description="e.g., LGA1700, AM5")
    chipset: Optional[str] = Field(None, description="e.g., Q670, B650")
    form_factor: Optional[str] = Field(None, description="e.g., MATX, ATX")

    # New fields for rich descriptions
    cpu_support: Optional[str] = Field(None, description="Supported CPU gens, e.g., 13VA-12VA (13th/12th Gen)")
    memory_type: Optional[str] = Field(None, description="Supported RAM, e.g., DDR5-5600, DDR4")
    slots: Optional[str] = Field(None, description="Expansion/Memory slots, e.g., 4DDR5, 2M.2")
    ports: Optional[str] = Field(None, description="Video/USB ports, e.g., 2DP, HDMI, 6USB")
    pcie_version: Optional[str] = Field(None, description="e.g., PCIE 4.0")


class RamSpecs(BaseProductSpecs):
    category_type: Literal["MEMORIA RAM"] = "MEMORIA RAM"
    capacity: Optional[str] = Field(None, description="Total capacity, e.g., 16GB")
    type: Optional[str] = Field(None, description="e.g., DDR4, DDR5")
    speed: Optional[str] = Field(None, description="Speed, e.g., 3200MHz")
    latency: Optional[str] = Field(None, description="CAS Latency, e.g., CL16")
    pins: Optional[str] = Field(None, description="e.g., 288-Pin")


class GpuSpecs(BaseProductSpecs):
    category_type: Literal["TARJETA DE VIDEO"] = "TARJETA DE VIDEO"
    chipset: Optional[str] = Field(None, description="e.g., NVIDIA RTX 3060")
    vram: Optional[str] = Field(None, description="Video memory, e.g., 12GB GDDR6")
    bus_width: Optional[str] = Field(None, description="e.g., 192BIT")
    interface: Optional[str] = Field(None, description="e.g., PCIE 4.0")
    cooling: Optional[str] = Field(None, description="Fan count, e.g., 3VENT (3 Fans)")


class ChassisSpecs(BaseProductSpecs):
    """
    PC Cases and Drive Enclosures.
    'CASE' in your data contains both PC Chassis and HDD Enclosures.
    """

    category_type: Literal["CASE"] = "CASE"
    type: Optional[str] = Field(None, description="PC Case, HDD Enclosure, SSD Enclosure")
    form_factor_support: Optional[str] = Field(None, description="Motherboard size (ATX) or Drive size (2.5 inch)")
    connections: Optional[str] = Field(None, description="Front ports or Interface, e.g., USB 3.2 Gen2")


class PowerSupplySpecs(BaseProductSpecs):
    category_type: Literal["FUENTES DE PODER"] = "FUENTES DE PODER"
    wattage: Optional[str] = Field(None, description="Power output, e.g., 650W")
    certification: Optional[str] = Field(None, description="e.g., 80 PLUS GOLD")
    standard: Optional[str] = Field(None, description="e.g., ATX3.1 Ready")
    fan_size: Optional[str] = Field(None, description="e.g., 120mm")


# --- 3. Storage ---
class StorageSpecs(BaseProductSpecs):
    """HDDs, SSDs, SD Cards, Flash Memory"""

    category_type: Literal["UNIDADES DE ESTADO SOLIDO Y DISCOS DUROS", "MEMORIA SD", "FLASH MEMORY"] = "UNIDADES DE ESTADO SOLIDO Y DISCOS DUROS"
    type: Optional[str] = Field(None, description="HDD, SSD, Micro-SD, USB Flash")
    capacity: Optional[str] = Field(None, description="Size, e.g., 2TB, 128GB")
    interface: Optional[str] = Field(None, description="e.g., SATA 6.0GB/s, USB 3.2")
    rpm: Optional[str] = Field(None, description="Rotational speed for HDDs, e.g., 5400RPM")
    cache: Optional[str] = Field(None, description="Buffer size, e.g., 512MB")
    form_factor: Optional[str] = Field(None, description="e.g., 3.5 inch, M.2")
    application: Optional[str] = Field(None, description="Usage, e.g., NAS, CCTV (Purple/Red)")


# --- 4. Displays & Imaging ---
class DisplaySpecs(BaseProductSpecs):
    """Monitors, TVs, Projectors"""

    category_type: Literal["MONITORES Y TELEVISORES", "PROYECTORES"] = "MONITORES Y TELEVISORES"
    device_type: Optional[str] = Field(None, description="Monitor, Projector, TV")
    screen_size: Optional[str] = Field(None, description="Size, e.g., 27 Inch")
    resolution: Optional[str] = Field(None, description="e.g., 5K, 4K")
    brightness: Optional[str] = Field(None, description="e.g., 8000Lum (for projectors)")
    refresh_rate: Optional[str] = Field(None, description="e.g., 60Hz")


class ImagingSpecs(BaseProductSpecs):
    """Printers, Scanners (Document & Barcode), Cameras"""

    category_type: Literal["CAMARAS", "ESCANER", "IMPRESORAS"] = "CAMARAS"
    device_type: Optional[str] = Field(None, description="Printer, Barcode Scanner, Webcam, Document Scanner")
    resolution: Optional[str] = Field(None, description="e.g., 720P, 1D/2D (for scanners)")
    speed: Optional[str] = Field(None, description="Print/Scan speed, e.g., 39PPM, 300 Scans")
    connectivity: Optional[str] = Field(None, description="e.g., USB, WIFI DIRECT, Ethernet")


# --- 5. Peripherals & Audio ---
class InputDeviceSpecs(BaseProductSpecs):
    category_type: Literal["MOUSE", "TECLADOS", "JOYSTICK"] = "MOUSE"
    device_type: Optional[str] = Field(None, description="Mouse, Keyboard, Combo, Gamepad")
    connectivity: Optional[str] = Field(None, description="Wireless 2.4G, USB, Bluetooth")
    dpi: Optional[str] = Field(None, description="Sensitivity, e.g., 1200dpi")
    features: Optional[str] = Field(None, description="e.g., Silent, RGB, Mechanical")


class AudioSpecs(BaseProductSpecs):
    category_type: Literal["PARLANTES"] = "PARLANTES"
    power: Optional[str] = Field(None, description="Output power, e.g., 200W-RMS, 3WATTS")
    features: Optional[str] = Field(None, description="e.g., RGB, USB, MIC")
    driver_size: Optional[str] = Field(None, description="Woofer size, e.g., 15 INCH")


# --- 6. Connectivity & Infrastructure ---
class NetworkSpecs(BaseProductSpecs):
    """Routers, Switches, Cabling, Accessories"""

    category_type: Literal["ROUTER, ACCESS POINT, SWITCH, NVR"] = "ROUTER, ACCESS POINT, SWITCH, NVR"
    device_type: Optional[str] = Field(None, description="Router, Switch, Access Point, NVR, Cabling/Accessory")
    specs: Optional[str] = Field(None, description="Technical specs like Voltage, Speed, Ports")


class UpsSpecs(BaseProductSpecs):
    category_type: Literal["UPS, REGULADORES"] = "UPS, REGULADORES"
    capacity: Optional[str] = Field(None, description="e.g., 36W, 1000VA")
    voltage: Optional[str] = Field(None, description="e.g., 12V CC")
    application: Optional[str] = Field(None, description="e.g., for Routers, IP Cameras")


# --- 7. Mobile & Tablets ---
class MobileSpecs(BaseProductSpecs):
    category_type: Literal["CELULARES", "TABLET"] = "CELULARES"
    ram: Optional[str] = Field(None, description="RAM")
    storage: Optional[str] = Field(None, description="Storage")
    screen_size: Optional[str] = Field(None, description="Screen size")
    network: Optional[str] = Field(None, description="e.g., LTE, WIFI")
    features: Optional[str] = Field(None, description="e.g., Rugged Case")


# --- 8. Miscellaneous Categories ---
class HomeApplianceSpecs(BaseProductSpecs):
    """'LINEA BLANCA' - Robot vacuums, etc."""

    category_type: Literal["LINEA BLANCA"] = "LINEA BLANCA"
    device_type: Optional[str] = Field(None, description="Robot Vacuum, Fridge, etc.")
    features: Optional[str] = Field(None, description="e.g., LiDAR, 5300Pa suction")


class CarryingCaseSpecs(BaseProductSpecs):
    """'MALETAS, MOCHILAS' - Tablet cases, Backpacks"""

    category_type: Literal["MALETAS, MOCHILAS"] = "MALETAS, MOCHILAS"
    compatible_with: Optional[str] = Field(None, description="Device compatibility, e.g., Tablet G PAD 10.1")
    material_or_type: Optional[str] = Field(None, description="Backpack, Sleeve, Rugged Case")


class ServiceSpecs(BaseProductSpecs):
    """'SOFTWARE' - Warranties, Licenses"""

    category_type: Literal["SOFTWARE"] = "SOFTWARE"
    service_type: Optional[str] = Field(None, description="Warranty, License, Subscription")
    duration: Optional[str] = Field(None, description="e.g., 1y (1 year)")
    compatible_device: Optional[str] = Field(None, description="e.g., Epson DS530II")


class GenericSpecs(BaseProductSpecs):
    """Catch-all for 'ACCESORIOS' or undefined items"""

    category_type: Literal["ACCESORIOS"] = "ACCESORIOS"
    summary: Optional[str] = Field(None, description="Brief description of the item")


# --- THE UNION ---
ProductSpecUnion = Union[
    NotebookSpecs,
    DesktopSpecs,
    ProcessorSpecs,
    MotherboardSpecs,
    RamSpecs,
    GpuSpecs,
    ChassisSpecs,
    PowerSupplySpecs,
    StorageSpecs,
    DisplaySpecs,
    ImagingSpecs,
    InputDeviceSpecs,
    AudioSpecs,
    NetworkSpecs,
    UpsSpecs,
    MobileSpecs,
    HomeApplianceSpecs,
    CarryingCaseSpecs,
    ServiceSpecs,
    GenericSpecs,
]
