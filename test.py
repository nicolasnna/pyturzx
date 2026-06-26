from drivers.turzx_52 import TurZX52Driver

if __name__ == "__main__":
    driver = TurZX52Driver()
    if driver.connect():
        resp = driver.set_brightness(100)
        print(resp)
