import psutil
import tkinter as tk
from tkinter import scrolledtext, ttk
from threading import Thread
from time import sleep
from collections import deque
from ttkbootstrap import Style
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import queue

class SystemMonitor(tk.Tk):
    def __init__(self):
        super().__init__()

        # Aquí se agrega una cola para manejar las actualizaciones de la GUI desde otros hilos
        self.queue = queue.Queue()
        self.check_queue()

        self.title("Monitor de Sistema")
        Style('lumen').theme_use()

        # Variables para almacenar el historial de uso
        self.cpu_history = deque(maxlen=60)
        self.ram_history = deque(maxlen=60)
        self.disk_history = deque(maxlen=60)

        # Frame para los recursos
        self.resources_frame = ttk.Frame(self)
        self.resources_frame.pack()

        # Get the screen size
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        # Set the window size to be slightly smaller than the screen size
        window_width = int(screen_width * 0.8)
        window_height = int(screen_height)

        self.geometry(f"{window_width}x{window_height}")

        # Labels para mostrar el uso actual de recursos
        self.cpu_label = ttk.Label(self.resources_frame, text='CPU: 0%')
        self.cpu_label.grid(row=0, column=0)
        self.ram_label = ttk.Label(self.resources_frame, text='RAM: 0%')
        self.ram_label.grid(row=0, column=1)
        self.disk_label = ttk.Label(self.resources_frame, text='Disco: 0%')
        self.disk_label.grid(row=0, column=2)
        self.network_label = ttk.Label(self.resources_frame, text='Red: Enviado 0 B, Recibido 0 B')
        self.network_label.grid(row=1, column=0, columnspan=3)

        # Labels para mostrar información del sistema
        self.system_info_frame = ttk.Frame(self)
        self.system_info_frame.pack()
        self.threads_label = ttk.Label(self.system_info_frame, text="Threads: 0")
        self.threads_label.grid(row=0, column=0)
        self.processes_label = ttk.Label(self.system_info_frame, text="Procesos: 0")
        self.processes_label.grid(row=0, column=1)

        canvas1 = tk.Canvas(self)
        canvas1.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Agregar una barra de desplazamiento vertical al Canvas
        scrollbar1 = ttk.Scrollbar(self, orient=tk.VERTICAL, command=canvas1.yview)
        scrollbar1.pack(side=tk.RIGHT, fill=tk.Y)

        # Configurar el Canvas para usar la barra de desplazamiento vertical
        canvas1.configure(yscrollcommand=scrollbar1.set)
        canvas1.bind("<Configure>", lambda e: canvas1.configure(scrollregion=canvas1.bbox("all")))

        # Crear un Frame que contendrá todos los elementos
        main_frame1 = ttk.Frame(canvas1)

        # Configurar el Frame en el Canvas
        canvas1.create_window((0, 0), window=main_frame1, anchor="nw")

        # Configurar el desplazamiento del Canvas con la rueda del mouse
        canvas1.bind_all("<MouseWheel>", lambda e: canvas1.yview_scroll(int(-1 * (e.delta / 120)), "units"))

        # Frame para los recursos
        self.resources_frame1 = ttk.Frame(main_frame1)
        self.resources_frame1.pack()

        # Create a frame to hold the text area and figures
        self.graphs_and_text_frame = ttk.Frame(self.resources_frame1)
        self.graphs_and_text_frame.pack()

        self.process_text_frame = ttk.Frame(self.graphs_and_text_frame, padding=20)
        self.process_text_frame.grid(row=0, column=0)

        # Área de texto para mostrar la lista de procesos
        self.process_text = scrolledtext.ScrolledText(self.process_text_frame, width=45)
        self.process_text.pack(fill=tk.BOTH, expand=True)

        # Figuras para mostrar el historial de uso de recursos
        self.cpu_figure, self.cpu_plot, self.cpu_canvas = self.setup_figure('Historial de Uso CPU (%)',
                                                                            'Tiempo (segundos)', 'Uso (%)')
        self.cpu_canvas.get_tk_widget().grid(row=0, column=1)

        self.ram_figure, self.ram_plot, self.ram_canvas = self.setup_figure('Historial de Uso RAM (%)',
                                                                            'Tiempo (segundos)', 'Uso (%)')
        self.ram_canvas.get_tk_widget().grid(row=1, column=1)

        self.disk_figure, self.disk_plot, self.disk_canvas = self.setup_figure('Historial de Uso del Disco (%)',
                                                                               'Tiempo (segundos)', 'Uso (%)')
        self.disk_canvas.get_tk_widget().grid(row=2, column=1)

        # Crear y comenzar hilos para el monitoreo del sistema
        self.running = True
        self.cpu_thread = Thread(target=self.update_cpu, daemon=True)
        self.ram_thread = Thread(target=self.update_ram, daemon=True)
        self.disk_thread = Thread(target=self.update_disk, daemon=True)
        self.network_thread = Thread(target=self.update_network, daemon=True)
        self.process_thread = Thread(target=self.update_processes, daemon=True)
        self.threads_thread = Thread(target=self.update_threads, daemon=True)
        self.processes_thread = Thread(target=self.update_processes_count, daemon=True)

        self.cpu_thread.start()
        sleep(0.2)  # Stagger thread start
        self.ram_thread.start()
        sleep(0.2)
        self.disk_thread.start()
        sleep(0.2)
        self.network_thread.start()
        sleep(0.2)
        self.process_thread.start()
        sleep(0.2)
        self.threads_thread.start()
        sleep(0.2)
        self.processes_thread.start()

        # Cerrar hilos cuando se cierre la ventana
        self.protocol("WM_DELETE_WINDOW", self.stop_threads)

    def setup_figure(self, title, xlabel, ylabel):
        figure = plt.figure(figsize=(7.5, 5))
        plot = figure.add_subplot(111)
        plot.set_title(title)
        plot.set_xlabel(xlabel)
        plot.set_ylabel(ylabel)
        canvas = FigureCanvasTkAgg(figure, master=self.graphs_and_text_frame)
        return figure, plot, canvas

    def check_queue(self):
        while not self.queue.empty():
            task = self.queue.get()
            task()
        self.after(100, self.check_queue)

    def update_cpu(self):
        while self.running:
            usage = psutil.cpu_percent()
            self.cpu_history.append(usage)
            self.queue.put(lambda: self.cpu_label.configure(text=f"CPU: {usage}%"))
            self.queue.put(
                lambda: self.update_graph(self.cpu_history, self.cpu_plot, self.cpu_canvas, 'CPU Usage', 'Time (s)',
                                          'Usage (%)'))
            sleep(1)

    def update_ram(self):
        while self.running:
            usage = psutil.virtual_memory().percent
            self.ram_history.append(usage)
            self.queue.put(lambda: self.ram_label.configure(text=f"RAM: {usage}%"))
            self.queue.put(
                lambda: self.update_graph(self.ram_history, self.ram_plot, self.ram_canvas, 'RAM Usage', 'Time (s)',
                                          'Usage (%)'))
            sleep(1)

    def update_disk(self):
        while self.running:
            usage = psutil.disk_usage('/').percent
            self.disk_history.append(usage)
            self.queue.put(lambda: self.disk_label.configure(text=f"Disco: {usage}%"))
            self.queue.put(
                lambda: self.update_graph(self.disk_history, self.disk_plot, self.disk_canvas, 'Disk Usage', 'Time (s)',
                                          'Usage (%)'))
            sleep(1)

    def update_network(self):
        old_value = psutil.net_io_counters()
        while self.running:
            sleep(1)
            new_value = psutil.net_io_counters()
            sent = self.format_bytes(new_value.bytes_sent - old_value.bytes_sent)
            received = self.format_bytes(new_value.bytes_recv - old_value.bytes_recv)
            self.network_label.configure(text=f"Red: Enviado {sent}, Recibido {received}")
            old_value = new_value

    def update_processes(self):
        while self.running:
            self.process_text.delete('1.0', tk.END)
            for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
                memory = self.format_bytes(proc.info['memory_info'].rss)
                self.process_text.insert(tk.END, f"{proc.info['name']} (PID: {proc.info['pid']}) - RAM: {memory}\n")
            sleep(5)

    def update_threads(self):
        while self.running:
            self.threads_label.configure(text=f"Threads: {psutil.Process().num_threads()}")
            sleep(5)

    def update_processes_count(self):
        while self.running:
            self.processes_label.configure(text=f"Procesos: {len(psutil.pids())}")
            sleep(5)

    def update_graph(self, history, plot, canvas, title, xlabel, ylabel):
        plot.clear()
        plot.set_title(title)
        plot.set_xlabel(xlabel)
        plot.set_ylabel(ylabel)
        plot.plot(history)
        canvas.draw()

    def format_bytes(self, size):
        # this function will convert bytes to MB.... GB... etc
        power = 2 ** 10
        n = 0
        power_labels = {0: '', 1: 'Ki', 2: 'Mi', 3: 'Gi', 4: 'Ti'}
        while size > power:
            size /= power
            n += 1
        return f"{size:.2f} {power_labels[n]}B"

    def stop_threads(self):
        self.running = False
        self.destroy()


if __name__ == "__main__":
    monitor = SystemMonitor()
    monitor.mainloop()