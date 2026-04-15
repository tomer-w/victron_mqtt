"""A utility to visualize and interact with Victron Venus OS devices and metrics.

Features:
- Hierarchical device tree showing parent/child relationships
- Metrics pane showing metrics for the selected device
- Live-updating metric values with color-coded metric kinds
- Search/filter for devices and metrics
- Double-click writable metrics to edit values inline
- Status bar with connection info, device count, installation ID
"""

import argparse
import asyncio
import inspect
import logging
import os
import tkinter as tk
from logging import getLogger
from tkinter import messagebox, simpledialog, ttk

from victron_mqtt import Device, Hub, Metric
from victron_mqtt.constants import MetricKind, OperationMode
from victron_mqtt.writable_metric import WritableMetric

DEFAULT_HOST = "venus.local."
DEFAULT_PORT = 1883
DEFAULT_USER = ""
DEFAULT_PASSWORD = ""

LOGGER = getLogger(__name__)

asyncio_loop: asyncio.AbstractEventLoop | None = None

# Color scheme for metric kinds
METRIC_KIND_COLORS = {
    MetricKind.SENSOR: "#2196F3",
    MetricKind.BINARY_SENSOR: "#9C27B0",
    MetricKind.SWITCH: "#FF9800",
    MetricKind.SELECT: "#FF5722",
    MetricKind.NUMBER: "#4CAF50",
    MetricKind.BUTTON: "#795548",
    MetricKind.TIME: "#607D8B",
    MetricKind.DEVICE_TRACKER: "#E91E63",
}

DEVICE_TYPE_ICONS = {
    "system": "🖥️",
    "battery": "🔋",
    "solar_charger": "☀️",
    "grid": "⚡",
    "inverter": "🔌",
    "generator": "⛽",
    "gps": "📍",
    "switch": "💡",
    "tank": "🪣",
    "temperature": "🌡️",
    "evcharger": "🚗",
}


class ConnectionDialog(simpledialog.Dialog):
    """Dialog to prompt for connection information."""

    def body(self, master):
        tk.Label(master, text="Server:").grid(row=0, sticky=tk.W, padx=5, pady=3)
        tk.Label(master, text="Port:").grid(row=1, sticky=tk.W, padx=5, pady=3)
        tk.Label(master, text="Username:").grid(row=2, sticky=tk.W, padx=5, pady=3)
        tk.Label(master, text="Password:").grid(row=3, sticky=tk.W, padx=5, pady=3)
        tk.Label(master, text="Use SSL:").grid(row=4, sticky=tk.W, padx=5, pady=3)
        host = os.environ.get("VICTRON_MQTT_SERVER", DEFAULT_HOST)
        port = os.environ.get("VICTRON_MQTT_PORT", DEFAULT_PORT)
        user = os.environ.get("VICTRON_MQTT_USER", DEFAULT_USER)
        password = os.environ.get("VICTRON_MQTT_PASSWORD", DEFAULT_PASSWORD)
        ssl = os.environ.get("VICTRON_MQTT_SSL", "") not in ["", "0", "False", "false", "F", "f", "No", "no", "N", "n"]

        self.server_entry = tk.Entry(master, width=30)
        self.server_entry.insert(0, host)

        self.port_entry = tk.Entry(master, width=30)
        self.port_entry.insert(0, str(port))

        self.username_entry = tk.Entry(master, width=30)
        self.username_entry.insert(0, user)

        self.password_entry = tk.Entry(master, show="*", width=30)
        self.password_entry.insert(0, password)

        self.use_ssl_var = tk.BooleanVar()
        self.use_ssl_check = tk.Checkbutton(master, variable=self.use_ssl_var)
        self.use_ssl_var.set(ssl)

        self.server_entry.grid(row=0, column=1, padx=5, pady=3)
        self.port_entry.grid(row=1, column=1, padx=5, pady=3)
        self.username_entry.grid(row=2, column=1, padx=5, pady=3)
        self.password_entry.grid(row=3, column=1, padx=5, pady=3)
        self.use_ssl_check.grid(row=4, column=1, sticky=tk.W, padx=5, pady=3)

        return self.server_entry

    def apply(self):
        server = self.server_entry.get()
        port = int(self.port_entry.get())
        username = self.username_entry.get()
        password = self.password_entry.get()
        use_ssl = self.use_ssl_var.get()
        self.result = (server, port, username, password, use_ssl)


class AttributeViewerDialog(simpledialog.Dialog):
    """Dialog to display properties and edit writable metrics with appropriate controls.
    Changes are applied immediately without needing to press OK."""

    def __init__(self, parent, instance):
        self.instance = instance
        self._writable_var = None
        self._applying = False
        title = f"Properties: {getattr(instance, 'name', str(instance))}"
        super().__init__(parent, title=title)

    def buttonbox(self):
        """Override to show only a Close button instead of OK/Cancel."""
        box = ttk.Frame(self)
        ttk.Button(box, text="Close", command=self.cancel, width=10).pack(padx=5, pady=5)
        box.pack()

    def body(self, master):
        # Properties section
        props_frame = ttk.LabelFrame(master, text="Properties", padding=5)
        props_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        row = 0
        for name, _value in inspect.getmembers(type(self.instance), lambda v: isinstance(v, property)):
            try:
                prop_value = getattr(self.instance, name)
                if isinstance(prop_value, Device | Metric | list | dict):
                    continue
                if callable(prop_value):
                    continue
                if prop_value is None:
                    continue
                ttk.Label(props_frame, text=f"{name}:", font=("", 9, "bold")).grid(
                    row=row, column=0, sticky=tk.W, padx=5, pady=2
                )
                value_label = ttk.Label(props_frame, text=str(prop_value))
                value_label.grid(row=row, column=1, sticky=tk.W, padx=5, pady=2)
                row += 1
            except AttributeError:
                continue

        if not isinstance(self.instance, WritableMetric):
            return master

        # Control section for writable metrics
        control_frame = ttk.LabelFrame(master, text="Control (changes apply immediately)", padding=5)
        control_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        descriptor = self.instance._descriptor
        kind = self.instance.metric_kind

        if kind == MetricKind.SWITCH:
            self._build_switch_control(control_frame, self.instance)
        elif kind == MetricKind.SELECT:
            self._build_select_control(control_frame, self.instance)
        elif kind in (MetricKind.NUMBER, MetricKind.TIME):
            self._build_number_control(control_frame, self.instance, descriptor)

        return master

    def _apply_value(self, value):
        """Apply a value change immediately to the writable metric."""
        if self._applying:
            return
        self._applying = True
        try:
            if isinstance(self.instance, WritableMetric):
                if self.instance.metric_kind in (MetricKind.NUMBER, MetricKind.TIME):
                    try:
                        self.instance.set(float(value))
                    except ValueError:
                        self.instance.set(value)
                else:
                    self.instance.set(value)
        finally:
            self._applying = False

    def _build_switch_control(self, parent, metric: WritableMetric):
        """Build an on/off toggle for switch metrics."""
        assert metric.enum_values is not None

        is_on = str(metric.value).lower() in ["on", "1", "true"]

        style = ttk.Style()
        style.configure("SwitchOnDot.TLabel", foreground="#2E7D32")
        style.configure("SwitchOffDot.TLabel", foreground="#C62828")

        btn_frame = ttk.Frame(parent)
        btn_frame.grid(row=0, column=0, columnspan=2, pady=5)

        on_frame = ttk.Frame(btn_frame)
        on_frame.pack(side=tk.LEFT, padx=5)
        ttk.Label(on_frame, text="●", style="SwitchOnDot.TLabel").pack(side=tk.LEFT, padx=(0, 4))
        self._on_btn = ttk.Button(
            on_frame,
            text="ON",
            width=10,
            command=lambda: self._set_switch("on"),
            state=tk.DISABLED if is_on else tk.NORMAL,
        )
        self._on_btn.pack(side=tk.LEFT)

        off_frame = ttk.Frame(btn_frame)
        off_frame.pack(side=tk.LEFT, padx=5)
        ttk.Label(off_frame, text="●", style="SwitchOffDot.TLabel").pack(side=tk.LEFT, padx=(0, 4))
        self._off_btn = ttk.Button(
            off_frame,
            text="OFF",
            width=10,
            command=lambda: self._set_switch("off"),
            state=tk.DISABLED if not is_on else tk.NORMAL,
        )
        self._off_btn.pack(side=tk.LEFT)

    def _set_switch(self, value: str):
        is_on = value == "on"
        self._on_btn.config(state=tk.DISABLED if is_on else tk.NORMAL)
        self._off_btn.config(state=tk.DISABLED if not is_on else tk.NORMAL)
        self._apply_value(value)

    def _build_select_control(self, parent, metric: WritableMetric):
        """Build a dropdown for select metrics. Shows display strings, sends enum ids."""
        assert metric.enum_values is not None
        assert metric._descriptor.enum is not None

        # Build string→id mapping
        enum_cls = metric._descriptor.enum
        self._select_string_to_id = {member.string: member.id for member in enum_cls}
        display_values = list(self._select_string_to_id.keys())

        # Show current value as display string
        current_display = str(metric.value)  # VictronEnum.__str__ returns .string
        self._writable_var = tk.StringVar(value=current_display)

        ttk.Label(parent, text="Select:", font=("", 9, "bold")).grid(row=0, column=0, sticky=tk.W, padx=5, pady=3)
        dropdown = ttk.Combobox(
            parent,
            textvariable=self._writable_var,
            values=display_values,
            state="readonly",
            width=25,
        )
        dropdown.grid(row=0, column=1, sticky=tk.W, padx=5, pady=3)
        dropdown.bind("<<ComboboxSelected>>", self._on_select_change)

    def _on_select_change(self, _event):
        """Send the enum id when a display string is selected."""
        display = self._writable_var.get()
        enum_id = self._select_string_to_id.get(display, display)
        self._apply_value(enum_id)

    def _build_number_control(self, parent, metric: WritableMetric, descriptor):
        """Build a slider + entry for number metrics with min/max/step."""
        current_value = float(metric.value) if metric.value is not None else 0.0
        min_val = float(descriptor.min) if descriptor.min is not None else 0.0
        max_val = float(descriptor.max) if descriptor.max is not None else 100.0
        step = float(descriptor.step) if descriptor.step is not None else 1.0
        precision = descriptor.precision or 0
        unit = metric.unit_of_measurement or ""

        self._writable_var = tk.StringVar(value=str(current_value))

        # Current value display
        ttk.Label(parent, text="Current:", font=("", 9, "bold")).grid(row=0, column=0, sticky=tk.W, padx=5, pady=3)
        self._value_display = ttk.Label(parent, text=f"{current_value} {unit}", font=("", 11))
        self._value_display.grid(row=0, column=1, sticky=tk.W, padx=5, pady=3)

        # Range info
        ttk.Label(parent, text="Range:", font=("", 9, "bold")).grid(row=1, column=0, sticky=tk.W, padx=5, pady=3)
        ttk.Label(parent, text=f"{min_val} - {max_val} {unit} (step: {step})").grid(
            row=1, column=1, sticky=tk.W, padx=5, pady=3
        )

        # Slider
        ttk.Label(parent, text="Set:", font=("", 9, "bold")).grid(row=2, column=0, sticky=tk.W, padx=5, pady=3)

        slider_frame = ttk.Frame(parent)
        slider_frame.grid(row=2, column=1, sticky="ew", padx=5, pady=3)

        ttk.Label(slider_frame, text=str(min_val), font=("", 8)).pack(side=tk.LEFT)

        self._slider = tk.Scale(
            slider_frame,
            from_=min_val,
            to=max_val,
            resolution=step,
            orient=tk.HORIZONTAL,
            length=250,
            showvalue=False,
            command=lambda v: self._on_slider_change(v, precision, unit),
        )
        self._slider.set(current_value)
        self._slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        ttk.Label(slider_frame, text=str(max_val), font=("", 8)).pack(side=tk.LEFT)

        # Entry for precise input with Apply button
        entry_frame = ttk.Frame(parent)
        entry_frame.grid(row=3, column=1, sticky=tk.W, padx=5, pady=3)

        self._number_entry = ttk.Entry(entry_frame, textvariable=self._writable_var, width=12)
        self._number_entry.pack(side=tk.LEFT)
        ttk.Label(entry_frame, text=f" {unit}  ").pack(side=tk.LEFT)
        ttk.Button(
            entry_frame, text="Apply", width=6, command=lambda: self._apply_value(self._writable_var.get())
        ).pack(side=tk.LEFT)

        # Sync entry → slider (visual only, no apply)
        self._writable_var.trace_add("write", lambda *_: self._sync_entry_to_slider(min_val, max_val))

    def _on_slider_change(self, value, precision, unit):
        val = round(float(value), precision)
        self._writable_var.set(str(val))
        self._value_display.config(text=f"{val} {unit}")
        self._apply_value(val)

    def _sync_entry_to_slider(self, min_val, max_val):
        try:
            val = float(self._writable_var.get())
            if min_val <= val <= max_val:
                self._slider.set(val)
        except (ValueError, tk.TclError):
            pass


class MetricContainer:
    """A UI container for a metric. Updates the tree view item when the metric changes."""

    def __init__(self, metric: Metric, tree_view: ttk.Treeview, parent_item: str):
        self._metric = metric
        self._metric.on_update = self._update
        self._tree_view = tree_view
        self._parent_item = parent_item

    def _update(self, metric: Metric, value):
        formatted = self._metric.format_value(value)
        if self._tree_view.exists(self._parent_item):
            self._tree_view.item(
                self._parent_item,
                values=(
                    formatted,
                    self._metric.metric_kind.value,
                    self._metric.unit_of_measurement or "",
                ),
            )


class App:
    def __init__(self, log_topic: str | None):
        self._log_topic = log_topic
        self.root = tk.Tk()
        self.root.resizable(True, True)
        self.root.geometry("1200x800")
        self.root.title("Victron Venus Metric Viewer")

        # --- Toolbar ---
        self.toolbar = ttk.Frame(self.root)
        self.toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=3)

        self.connect_button = ttk.Button(self.toolbar, text="🔌 Connect", command=self._connect)
        self.connect_button.pack(side=tk.LEFT, padx=2, pady=2)

        self.disconnect_button = ttk.Button(
            self.toolbar, text="⛔ Disconnect", command=self._disconnect, state=tk.DISABLED
        )
        self.disconnect_button.pack(side=tk.LEFT, padx=2, pady=2)

        self.info_button = ttk.Button(self.toolbar, text="Info", command=self._info, state=tk.DISABLED)
        self.info_button.pack(side=tk.LEFT, padx=10, pady=2)

        self.expand_button = ttk.Button(self.toolbar, text="📂 Expand All", command=self._expand_all, state=tk.DISABLED)
        self.expand_button.pack(side=tk.LEFT, padx=2, pady=2)

        self.collapse_button = ttk.Button(
            self.toolbar, text="📁 Collapse All", command=self._collapse_all, state=tk.DISABLED
        )
        self.collapse_button.pack(side=tk.LEFT, padx=2, pady=2)

        # --- Search bar ---
        ttk.Label(self.toolbar, text="🔍").pack(side=tk.LEFT, padx=(20, 2))
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", self._on_search)
        self.search_entry = ttk.Entry(self.toolbar, textvariable=self._search_var, width=25)
        self.search_entry.pack(side=tk.LEFT, padx=2, pady=2)

        self.clear_search_button = ttk.Button(self.toolbar, text="✕", width=3, command=self._clear_search)
        self.clear_search_button.pack(side=tk.LEFT, padx=2, pady=2)

        # --- Two-pane layout: devices (left) + metrics (right) ---
        pane = ttk.Panedwindow(self.root, orient=tk.HORIZONTAL)
        pane.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=3)

        devices_frame = ttk.Frame(pane)
        metrics_frame = ttk.Frame(pane)
        pane.add(devices_frame, weight=2)
        pane.add(metrics_frame, weight=3)

        ttk.Label(devices_frame, text="Devices", font=("", 10, "bold")).grid(
            row=0, column=0, sticky=tk.W, padx=2, pady=(0, 4)
        )
        self.device_tree = ttk.Treeview(devices_frame, selectmode="browse", columns=("type",))
        self.device_tree.bind("<<TreeviewSelect>>", self._on_device_select)
        self.device_tree.bind("<Double-1>", self._on_device_double_click)

        self.device_tree.heading("#0", text="Device", anchor=tk.W)
        self.device_tree.heading("type", text="Type", anchor=tk.W)
        self.device_tree.column("#0", width=300, minwidth=180)
        self.device_tree.column("type", width=180, minwidth=100)

        device_vsb = ttk.Scrollbar(devices_frame, orient="vertical", command=self.device_tree.yview)
        device_hsb = ttk.Scrollbar(devices_frame, orient="horizontal", command=self.device_tree.xview)
        self.device_tree.configure(yscrollcommand=device_vsb.set, xscrollcommand=device_hsb.set)
        self.device_tree.grid(row=1, column=0, sticky="nsew")
        device_vsb.grid(row=1, column=1, sticky="ns")
        device_hsb.grid(row=2, column=0, sticky="ew")
        devices_frame.grid_rowconfigure(1, weight=1)
        devices_frame.grid_columnconfigure(0, weight=1)
        self.device_tree.tag_configure("device", font=("", 10, "bold"))

        self._metrics_title_var = tk.StringVar(value="Metrics")
        ttk.Label(metrics_frame, textvariable=self._metrics_title_var, font=("", 10, "bold")).grid(
            row=0, column=0, sticky=tk.W, padx=2, pady=(0, 4)
        )
        self.metric_tree = ttk.Treeview(metrics_frame, selectmode="browse", columns=("value", "kind", "unit"))
        self.metric_tree.bind("<<TreeviewSelect>>", self._on_metric_select)
        self.metric_tree.bind("<Double-1>", self._on_metric_double_click)

        self.metric_tree.heading("#0", text="Metric", anchor=tk.W)
        self.metric_tree.heading("value", text="Value", anchor=tk.W)
        self.metric_tree.heading("kind", text="Kind", anchor=tk.W)
        self.metric_tree.heading("unit", text="Unit", anchor=tk.W)
        self.metric_tree.column("#0", width=350, minwidth=180)
        self.metric_tree.column("value", width=220, minwidth=100)
        self.metric_tree.column("kind", width=120, minwidth=80)
        self.metric_tree.column("unit", width=80, minwidth=50)

        metric_vsb = ttk.Scrollbar(metrics_frame, orient="vertical", command=self.metric_tree.yview)
        metric_hsb = ttk.Scrollbar(metrics_frame, orient="horizontal", command=self.metric_tree.xview)
        self.metric_tree.configure(yscrollcommand=metric_vsb.set, xscrollcommand=metric_hsb.set)
        self.metric_tree.grid(row=1, column=0, sticky="nsew")
        metric_vsb.grid(row=1, column=1, sticky="ns")
        metric_hsb.grid(row=2, column=0, sticky="ew")
        metrics_frame.grid_rowconfigure(1, weight=1)
        metrics_frame.grid_columnconfigure(0, weight=1)

        # Tag colors for metric kinds
        for kind, color in METRIC_KIND_COLORS.items():
            self.metric_tree.tag_configure(f"kind_{kind.value}", foreground=color)
        self.metric_tree.tag_configure("writable", foreground="#FF6F00")

        # --- Status bar ---
        self.status_frame = ttk.Frame(self.root, relief=tk.SUNKEN)
        self.status_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=2)

        self._status_connection = tk.StringVar(value="⚪ Disconnected")
        self._status_devices = tk.StringVar(value="")
        self._status_installation = tk.StringVar(value="")

        ttk.Label(self.status_frame, textvariable=self._status_connection).pack(side=tk.LEFT, padx=10)
        ttk.Separator(self.status_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        ttk.Label(self.status_frame, textvariable=self._status_devices).pack(side=tk.LEFT, padx=10)
        ttk.Separator(self.status_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        ttk.Label(self.status_frame, textvariable=self._status_installation).pack(side=tk.LEFT, padx=10)

        self._client = None
        self._metric_containers = []
        self._selected_device_id: str | None = None

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._to_quit = False

    def update(self):
        self.root.update()

    def _on_close(self):
        self._to_quit = True

    @property
    def to_quit(self):
        return self._to_quit

    def _refresh_info_button_state(self):
        has_device_selection = len(self.device_tree.selection()) > 0
        has_metric_selection = len(self.metric_tree.selection()) > 0
        self.info_button.config(state=tk.NORMAL if (has_device_selection or has_metric_selection) else tk.DISABLED)

    def _on_device_select(self, _event):
        if self._client is None:
            return
        selection = self.device_tree.selection()
        self._selected_device_id = selection[0][1:] if selection else None
        self._refill_metric_pane()
        self._refresh_info_button_state()

    def _on_metric_select(self, _event):
        self._refresh_info_button_state()

    def _on_device_double_click(self, event):
        """Handle double-click on a device node."""
        item = self.device_tree.identify_row(event.y)
        if not item or self._client is None:
            return
        device = self._client._devices.get(item[1:])
        if device is not None:
            AttributeViewerDialog(self.root, device)

    def _on_metric_double_click(self, event):
        """Handle double-click on a metric row."""
        item = self.metric_tree.identify_row(event.y)
        if not item or self._client is None:
            return
        metric = self._client.get_metric(item[1:])
        if metric is not None:
            AttributeViewerDialog(self.root, metric)

    def _expand_all(self):
        self._expand_all_recursive()

    def _expand_all_recursive(self):
        def _expand(item):
            self.device_tree.item(item, open=True)
            for child in self.device_tree.get_children(item):
                _expand(child)

        for item in self.device_tree.get_children():
            _expand(item)

    def _collapse_all(self):
        for item in self.device_tree.get_children():
            self.device_tree.item(item, open=False)

    def _clear_search(self):
        self._search_var.set("")

    def _on_search(self, *_args):
        query = self._search_var.get().lower().strip()
        self._refill_tree_filtered(query)

    def _refill_tree_filtered(self, query: str):
        """Rebuild tree showing only items matching query."""
        if self._client is None:
            return

        previous_selected_device_id = self._selected_device_id

        self.device_tree.delete(*self.device_tree.get_children())
        self.metric_tree.delete(*self.metric_tree.get_children())
        self._metric_containers.clear()
        self._selected_device_id = None

        all_devices = self._client._devices  # Access internal dict to include metric-less parents
        # Build device tree
        root_devices = [d for d in all_devices.values() if d.parent_device is None]
        root_devices.sort(key=lambda d: d.unique_id)

        for device in root_devices:
            self._insert_device_tree(device, "", all_devices, query)

        if query:
            # When filtering, expand everything so results are visible
            self._expand_all_recursive()
        else:
            # Auto-expand first level only
            for item in self.device_tree.get_children():
                self.device_tree.item(item, open=True)

        if previous_selected_device_id is not None:
            previous_iid = "D" + previous_selected_device_id
            if self.device_tree.exists(previous_iid):
                self.device_tree.selection_set(previous_iid)
                self.device_tree.focus(previous_iid)
                self._selected_device_id = previous_selected_device_id

        if self._selected_device_id is None:
            roots = self.device_tree.get_children()
            if roots:
                first_iid = roots[0]
                self.device_tree.selection_set(first_iid)
                self.device_tree.focus(first_iid)
                self._selected_device_id = first_iid[1:]

        self._refill_metric_pane()
        self._refresh_info_button_state()

    def _device_matches(self, device: Device, query: str, all_devices: dict) -> bool:
        """Check if device or any of its children/metrics match the query."""
        if not query:
            return True
        text = f"{device.name} {device.unique_id} {device.model or ''} {device.device_type.string}".lower()
        if query in text:
            return True
        # Check metrics
        for metric in device.metrics:
            metric_text = f"{metric.name} {metric.short_id} {metric.formatted_value}".lower()
            if query in metric_text:
                return True
        # Check children
        children = [d for d in all_devices.values() if d.parent_device is device]
        return any(self._device_matches(child, query, all_devices) for child in children)

    def _insert_device_tree(self, device: Device, parent_iid: str, all_devices: dict, query: str):
        """Insert a device and its children into the tree."""
        if not self._device_matches(device, query, all_devices):
            return

        icon = DEVICE_TYPE_ICONS.get(device.device_type.id, "📦")
        device_text = f"{icon} {device.name}"
        device_iid = "D" + device.unique_id

        self.device_tree.insert(
            parent_iid,
            "end",
            text=device_text,
            values=(device.device_type.string,),
            iid=device_iid,
            tags=("device",),
            open=True,
        )

        # Add child devices
        children = [d for d in all_devices.values() if d.parent_device is device]
        children.sort(key=lambda d: d.unique_id)
        for child in children:
            self._insert_device_tree(child, device_iid, all_devices, query)

    def _refill_metric_pane(self):
        """Refresh metrics pane for the currently selected device."""
        self.metric_tree.delete(*self.metric_tree.get_children())
        self._metric_containers.clear()

        if self._client is None or self._selected_device_id is None:
            self._metrics_title_var.set("Metrics")
            return

        device = self._client._devices.get(self._selected_device_id)
        if device is None:
            self._metrics_title_var.set("Metrics")
            return

        self._metrics_title_var.set(f"Metrics - {device.name} ({device.unique_id})")

        metrics = sorted(device.metrics, key=lambda x: x.short_id)
        for metric in metrics:
            tags = [f"kind_{metric.metric_kind.value}"]
            if isinstance(metric, WritableMetric):
                tags.append("writable")

            metric_iid = "M" + metric.unique_id
            metric_item = self.metric_tree.insert(
                "",
                "end",
                text=f"{metric.name or ''}",
                values=(
                    metric.formatted_value,
                    metric.metric_kind.value,
                    metric.unit_of_measurement or "",
                ),
                iid=metric_iid,
                tags=tuple(tags),
            )
            self._metric_containers.append(MetricContainer(metric, self.metric_tree, metric_item))

    async def _async_connect(
        self, server: str, port: int, username: str | None, password: str | None, use_ssl: bool
    ) -> bool:
        try:
            self._status_connection.set("🟡 Connecting...")
            self._client = Hub(
                server,
                port,
                username,
                password,
                use_ssl,
                topic_log_info=self._log_topic,
                operation_mode=OperationMode.EXPERIMENTAL,
                update_frequency_seconds=3,
            )
            await self._client.connect()
            self._status_connection.set("🟡 Waiting for data...")
            await self._client.wait_for_first_refresh()

            self._refill_tree_filtered("")

            device_count = len(self._client.devices)
            metric_count = sum(len(d.metrics) for d in self._client.devices.values())
            self._status_connection.set(f"🟢 Connected to {server}:{port}")
            self._status_devices.set(f"📊 {device_count} devices, {metric_count} metrics")
            self._status_installation.set(f"🆔 Installation: {self._client.installation_id}")

            self.disconnect_button.config(state=tk.NORMAL)
            self.expand_button.config(state=tk.NORMAL)
            self.collapse_button.config(state=tk.NORMAL)
            return True
        except Exception as e:
            LOGGER.exception("Error connecting to Venus device: %s", e)
            self._status_connection.set("🔴 Connection failed")
            messagebox.showerror("Error", f"Error connecting: {e}")
            self.connect_button.config(state=tk.NORMAL)
            return False

    def _fill_tree(self):
        """Legacy fill - use _refill_tree_filtered instead."""
        self._refill_tree_filtered("")

    def _info(self):
        if not self._client:
            return

        metric_selection = self.metric_tree.selection()
        if metric_selection:
            metric = self._client.get_metric(metric_selection[0][1:])
            if metric is not None:
                AttributeViewerDialog(self.root, metric)
            return

        device_selection = self.device_tree.selection()
        if device_selection:
            device = self._client._devices.get(device_selection[0][1:])
            if device is not None:
                AttributeViewerDialog(self.root, device)

    def _connect(self):
        self.connect_button.config(state=tk.DISABLED)

        if self._client is not None:
            self._disconnect()

        dialog = ConnectionDialog(self.root)
        if dialog.result:
            server, port, username, password, use_ssl = dialog.result
        else:
            self.connect_button.config(state=tk.NORMAL)
            return

        if server == "":
            server = DEFAULT_HOST
        if port == 0:
            port = DEFAULT_PORT
        if username == "":
            username = None
        if password == "":
            password = None

        async def connect():
            success = await self._async_connect(server, port, username, password, use_ssl)
            if not success:
                self.connect_button.config(state=tk.NORMAL)

        self._task = asyncio.create_task(connect())

    def _disconnect(self):
        self.disconnect_button.config(state=tk.DISABLED)
        self.info_button.config(state=tk.DISABLED)
        self.expand_button.config(state=tk.DISABLED)
        self.collapse_button.config(state=tk.DISABLED)
        self.device_tree.delete(*self.device_tree.get_children())
        self.metric_tree.delete(*self.metric_tree.get_children())
        self._metric_containers.clear()
        self._selected_device_id = None

        if self._client is not None:
            loop = asyncio.get_event_loop()
            asyncio.run_coroutine_threadsafe(self._client.disconnect(), loop)
            self._client = None

        self._status_connection.set("⚪ Disconnected")
        self._status_devices.set("")
        self._status_installation.set("")
        self.connect_button.config(state=tk.NORMAL)


async def run_app(log_topic: str | None):
    app = App(log_topic)
    global asyncio_loop  # noqa: PLW0603
    asyncio_loop = asyncio.get_running_loop()
    while not app.to_quit:
        app.update()
        await asyncio.sleep(0.01)


def main():
    parser = argparse.ArgumentParser(description="Victron Venus Metric Viewer")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable debug logging")
    parser.add_argument("--log-file", "-l", type=str, help="Log to a specified file")
    parser.add_argument("--log-topic", "-lt", type=str, help="Log level bump to a specified topic")
    args = parser.parse_args()

    log_level = logging.INFO if args.verbose else logging.WARNING
    log_config = {"level": log_level, "format": "%(asctime)s - %(name)s - %(levelname)s - [%(thread)d] - %(message)s"}

    if args.log_file:
        log_config["filename"] = args.log_file

    logging.basicConfig(**log_config)

    asyncio.run(run_app(args.log_topic))


if __name__ == "__main__":
    main()
