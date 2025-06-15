"""A simple utility to illustrate how to use the Victron Venus Client library
to connect to a Venus OS device and display the metrics."""

import asyncio
import inspect
from logging import getLogger
import tkinter as tk
from tkinter import simpledialog
import tkinter.ttk as ttk
from victron_mqtt import Hub, Device, Metric
from victron_mqtt.constants import DEFAULT_HOST, DEFAULT_PORT


LOGGER = getLogger(__name__)

"""Dialog to prompt for connection information"""


class ConnectionDialog(simpledialog.Dialog):
    """Dialog to prompt for connection information."""

    def body(self, master):
        tk.Label(master, text="Server:").grid(row=0)
        tk.Label(master, text="Port:").grid(row=1)
        tk.Label(master, text="Username:").grid(row=2)
        tk.Label(master, text="Password:").grid(row=3)
        tk.Label(master, text="Use SSL:").grid(row=4)

        self.server_entry = tk.Entry(master)
        self.server_entry.insert(0, DEFAULT_HOST)

        self.port_entry = tk.Entry(master)
        self.port_entry.insert(0, str(DEFAULT_PORT))

        self.username_entry = tk.Entry(master)

        self.password_entry = tk.Entry(master, show="*")

        self.use_ssl_var = tk.BooleanVar()
        self.use_ssl_check = tk.Checkbutton(master, variable=self.use_ssl_var)

        self.server_entry.grid(row=0, column=1)
        self.port_entry.grid(row=1, column=1)
        self.username_entry.grid(row=2, column=1)
        self.password_entry.grid(row=3, column=1)
        self.use_ssl_check.grid(row=4, column=1)

        return self.server_entry

    def apply(self):
        server = self.server_entry.get()
        port = int(self.port_entry.get())
        username = self.username_entry.get()
        password = self.password_entry.get()
        use_ssl = self.use_ssl_var.get()
        self.result = (server, port, username, password, use_ssl)


class AttributeViewerDialog(simpledialog.Dialog):
    """Dialog to display the attributes of an object."""

    def __init__(self, parent, instance):
        self.instance = instance
        super().__init__(parent, title="Attribute Viewer")

    def body(self, master):
        row = 0
        for name, value in inspect.getmembers(type(self.instance), lambda v: isinstance(v, property)):
            try:
                value = getattr(self.instance, name)
                if isinstance(value, (Device, Metric, list, dict)):
                    continue
                if callable(value):
                    continue
                ttk.Label(master, text=f"{name}:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
                ttk.Label(master, text=str(value)).grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)
                row += 1
            except AttributeError:
                continue

        return master

    def buttonbox(self):
        box = ttk.Frame(self)

        w = ttk.Button(box, text="OK", width=10, command=self.ok, default=tk.ACTIVE)
        w.pack(side=tk.LEFT, padx=5, pady=5)

        self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.cancel)

        box.pack()


class MetricContainer:
    """A UI orientated container for a metric. Updates the item in the tree view when the metric changes."""

    def __init__(self, metric: Metric, tree_view: ttk.Treeview, parent_item: str):
        self._metric = metric
        self._metric.on_update = self._update
        self._tree_view = tree_view
        self._parent_item = parent_item

    def _update(self, metric: Metric):  # pylint: disable=unused-argument
        formatted = self._metric.formatted_value
        self._tree_view.item(self._parent_item, values=(formatted,))


class App:
    def __init__(self):
        self.root = tk.Tk()

        self.root.resizable(True, True)
        self.root.geometry("1024x768")

        self.root = self.root
        self.root.title("Victron Venus Client")

        self.toolbar = ttk.Frame(self.root)
        self.toolbar.pack(side=tk.TOP, fill=tk.X)

        self.connect_button = ttk.Button(self.toolbar, text="Connect", command=self._connect)
        self.connect_button.pack(side=tk.LEFT, padx=2, pady=2)

        self.disconnect_button = ttk.Button(
            self.toolbar, text="Disconnect", command=self._disconnect, state=tk.DISABLED
        )
        self.disconnect_button.pack(side=tk.LEFT, padx=2, pady=2)

        self.info_button = ttk.Button(self.toolbar, text="Info", command=self._info, state=tk.DISABLED)
        self.info_button.pack(side=tk.LEFT, padx=10, pady=2)

        self.tree = ttk.Treeview(self.root, selectmode="browse")
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.tree.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.tree["columns"] = "value"
        self.tree.heading("#0", text="Item")
        self.tree.heading("value", text="Value")

        self._client = None
        self._metric_containers = []

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._to_quit = False

    def update(self):
        self.root.update()

    def _on_close(self):
        self._to_quit = True

    @property
    def to_quit(self):
        return self._to_quit

    def _on_tree_select(self, event):  # pylint: disable=unused-argument
        if len(self.tree.selection()) == 0:  # nothing selected
            if str(self.info_button["state"]) == tk.NORMAL:
                self.info_button.config(state=tk.DISABLED)
        else:
            if str(self.info_button["state"]) == tk.DISABLED:
                self.info_button.config(state=tk.NORMAL)

    async def _async_connect(self, server: str, port: int, username: str, password: str, use_ssl: bool) -> bool:
        try:
            self._client = Hub(server, port, username, password, use_ssl)
            await self._client.connect()
            await self._client.initialize_devices_and_metrics()
            self._fill_tree()
            self.disconnect_button.config(state=tk.NORMAL)
        except Exception as e:  # pylint: disable=broad-except
            message = str(e)
            if message == "":
                message = type(e).__name__
            simpledialog.messagebox.showerror("Error", f"Error connecting: {message}")
            await self._client.disconnect()
            self.connect_button.config(state=tk.NORMAL)

    def _fill_tree(self):
        for device in self._client.devices:
            device_item = self.tree.insert(
                "",
                "end",
                text=device.model,
                values=(device.serial_number, ""),
                iid="D" + device.unique_id,
            )
            metrics = device.metrics
            metrics.sort(key=lambda x: (x.phase if len(x.phase) > 0 else "L0") + x.short_id)
            for metric in metrics:
                metric_item = self.tree.insert(
                    device_item,
                    "end",
                    text=metric.short_id,
                    values=(metric.formatted_value,),
                    iid="M" + metric.unique_id,
                )
                self._metric_containers.append(MetricContainer(metric, self.tree, metric_item))

    def _info(self):
        item = self.tree.selection()[0]
        unique_id = item[1:]
        if item[0] == "D":
            device = self._client.get_device_from_unique_id(unique_id)
            if device is not None:
                AttributeViewerDialog(self.root, device)
        elif item[0] == "M":
            metric = self._client.get_metric_from_unique_id(unique_id)
            if metric is not None:
                AttributeViewerDialog(self.root, metric)

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

        asyncio.run_coroutine_threadsafe(
            self._async_connect(server, port, username, password, use_ssl),
            asyncio.get_event_loop(),
        )

    def _disconnect(self):
        self.disconnect_button.config(state=tk.DISABLED)
        self.info_button.config(state=tk.DISABLED)
        self.tree.delete(*self.tree.get_children())

        if self._client is not None:
            loop = asyncio.get_event_loop()
            asyncio.run_coroutine_threadsafe(self._client.disconnect(), loop)
            self._client = None

        self.connect_button.config(state=tk.NORMAL)


def main():
    app = App()

    async def main_loop():
        while not app.to_quit:
            app.update()
            await asyncio.sleep(0.01)

    asyncio.run(main_loop())


if __name__ == "__main__":
    main()
