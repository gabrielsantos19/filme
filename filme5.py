from multiprocessing import Process, Queue
import time
import mss
import mss.tools
import os


def screenshotter(queue):
    screenshotsPerSecond = 144
    localQueue = []
    screenshotsToTake = screenshotsPerSecond
    # Adjust this to select the screen area to grab.
    # The smaller the area, the better the performance.
    # For a big area, the algorithm might not be able to keep up.
    monitor = {"top": 300, "left": 100, "width": 400, "height": 200}
    
    with mss.mss() as sct:
        now_ns = time.time_ns()
        endPeriod = now_ns + 1000000000

        while True:
            now_ns = time.time_ns()

            if screenshotsToTake:
                localQueue.append(( now_ns, sct.grab(monitor) ))
                screenshotsToTake -= 1

            # if the 1 second period is over
            if now_ns > endPeriod:
                queue.put(localQueue)
                localQueue = []
                endPeriod += 1000000000
                screenshotsToTake = screenshotsPerSecond


def save(queue):
    outputFolder = "screenshots"
    to_png = mss.tools.to_png

    while True:
        localQueue = queue.get()
        frameNumber = 0

        for (timestamp, img) in localQueue:
            localTime = time.localtime(timestamp / 1000000000)
            strTime = time.strftime("%X", localTime)
            ns = timestamp % 1000000000
            filename = f"{outputFolder}/{strTime}.{ns:09d}#{frameNumber}.png"
            to_png(img.rgb, img.size, output=filename)
            frameNumber += 1

        localQueue = []


def main():
    print("Started. Press Ctrl+c to exit.")

    if not os.path.exists("screenshots"):
        os.makedirs("screenshots")
        print("Created folder screenshots to paste the images.")

    queue = Queue()

    p1 = Process(target=screenshotter, args=(queue,))
    p1.start()
    p2 = Process(target=save, args=(queue,))
    p2.start()
    p3 = Process(target=save, args=(queue,))
    p3.start()
    
    try:
        p1.join()
    except KeyboardInterrupt as e:
        print(e)

    p1.terminate()
    p2.terminate()
    p3.terminate()
    print("Exited successfully.")


if __name__ == "__main__":
    main()