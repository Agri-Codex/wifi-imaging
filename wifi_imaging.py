import tkinter as tk
from tkinter import ttk, filedialog
import pywifi
import threading
import time
import pandas as pd

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

SCAN_INTERVAL = 1
network_history = {}
scan_data = []

wifi = pywifi.PyWiFi()
iface = wifi.interfaces()[0]

root = tk.Tk()
root.title('WiFi Imaging')
root.geometry('1400x850')
root.configure(bg='#111111')

style = ttk.Style()
style.theme_use('clam')

style.configure('Treeview', background='#1e1e1e', foreground='white', fieldbackground='#1e1e1e', rowheight=28)
style.configure('Treeview.Heading', background='#333333', foreground='white')

columns = ('SSID', 'MAC', 'Signal', 'Channel', 'Frequency', 'Band', 'Fluctuation')

tree = ttk.Treeview(root, columns=columns, show='headings')

for col in columns:
    tree.heading(col, text=col)
    tree.column(col, width=150)

tree.pack(fill='both', expand=True, padx=10, pady=10)

fig = Figure(figsize=(10, 4), dpi=100)
ax = fig.add_subplot(111)

fig.patch.set_facecolor('#111111')
ax.set_facecolor('#1e1e1e')

canvas = FigureCanvasTkAgg(fig, master=root)
canvas.get_tk_widget().pack(fill='both', expand=True)

heatmap_canvas = tk.Canvas(root, width=600, height=250, bg='#1e1e1e', highlightthickness=0)
heatmap_canvas.pack(pady=10)


def get_band(freq):
    if freq < 3000:
        return '2.4 GHz'
    return '5 GHz'


def draw_heatmap(networks):
    heatmap_canvas.delete('all')

    cols = 5
    size = 100

    for idx, net in enumerate(networks[:10]):
        row = idx // cols
        col = idx % cols

        x1 = col * size + 10
        y1 = row * size + 10

        signal = abs(net.signal)
        intensity = max(0, 255 - signal * 2)
        color = f'#{intensity:02x}0000'

        heatmap_canvas.create_rectangle(x1, y1, x1 + 80, y1 + 80, fill=color, outline='')
        heatmap_canvas.create_text(x1 + 40, y1 + 40, text=net.ssid[:10], fill='white')


def update_graph():
    ax.clear()

    ax.set_facecolor('#1e1e1e')
    ax.set_title('Signal Strength Changes', color='white')
    ax.set_xlabel('Time', color='white')
    ax.set_ylabel('RSSI', color='white')

    for ssid, values in network_history.items():
        ax.plot(values[-20:], label=ssid)

    ax.legend(loc='upper right', fontsize=8)
    canvas.draw()


def scan_wifi():
    while True:
        try:
            iface.scan()
            time.sleep(1)

            results = iface.scan_results()
            tree.delete(*tree.get_children())

            current_networks = []

            for net in results:
                ssid = net.ssid or 'Hidden'
                mac = net.bssid
                signal = net.signal
                freq = net.freq

                band = get_band(freq)

                if ssid not in network_history:
                    network_history[ssid] = []

                network_history[ssid].append(signal)

                if len(network_history[ssid]) > 50:
                    network_history[ssid].pop(0)

                fluctuation = 0

                if len(network_history[ssid]) >= 2:
                    fluctuation = abs(network_history[ssid][-1] - network_history[ssid][-2])

                fluctuation_text = 'Movement Detected' if fluctuation > 5 else 'Stable'

                tree.insert('', tk.END, values=(ssid, mac, signal, '-', freq, band, fluctuation_text))

                scan_data.append({
                    'SSID': ssid,
                    'MAC': mac,
                    'Signal': signal,
                    'Frequency': freq,
                    'Band': band,
                    'Fluctuation': fluctuation
                })

                current_networks.append(net)

            draw_heatmap(current_networks)
            update_graph()

        except Exception as e:
            print('Error:', e)

        time.sleep(SCAN_INTERVAL)


def export_csv():
    if not scan_data:
        return

    file_path = filedialog.asksaveasfilename(defaultextension='.csv', filetypes=[('CSV files', '*.csv')])

    if file_path:
        df = pd.DataFrame(scan_data)
        df.to_csv(file_path, index=False)


export_btn = tk.Button(root, text='Export CSV', command=export_csv, bg='#333333', fg='white')
export_btn.pack(pady=10)

scanner_thread = threading.Thread(target=scan_wifi, daemon=True)
scanner_thread.start()

root.mainloop()
