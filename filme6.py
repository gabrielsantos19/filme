from multiprocessing import Process, Queue
import numpy
import time
import mss
import mss.tools
import os
import cv2


def screenshotter(queue):
    screenshotsPerSecond = 144
    localQueue = []
    screenshotsToTake = screenshotsPerSecond
    # Adjust this to select the screen area to grab.
    # The smaller the area, the better the performance.
    # For a big area, the algorithm might not be able to keep up
    # with the chosen fps.
    monitor = {"top": 110, "left": 0, "width": 480, "height": 360}
    
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


def writer(args):
    queue = args[0]
    splitQueue = args[1]
    outputFolder = "videosToSplit"
    to_png = mss.tools.to_png
    fourcc = cv2.VideoWriter_fourcc(*'DIVX')

    while True:
        localQueue = queue.get()

        (timestamp, img) = localQueue[0]
        localTime = time.localtime(timestamp / 1000000000)
        strTime = time.strftime("%X", localTime)
        ns = timestamp % 1000000000

        name = f"{strTime}.{ns:09d}"
        filename = f"{outputFolder}/{name}.avi"
        
        out = cv2.VideoWriter(filename, fourcc, len(localQueue), img.size)

        for (timestamp, img) in localQueue:
            img = numpy.array(img)
            img = numpy.flip(img[:, :, :3], 2)
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            out.write(img)

        out.release()
        localQueue = []
        splitQueue.put((name, filename))


def splitter(queue):
    while True:
        name, filename = queue.get()
        vidcap = cv2.VideoCapture(filename)
        success, image = vidcap.read()
        frameNumber = 0

        while success:
            cv2.imwrite(f"screenshots/{name}#{frameNumber}.jpg", image)
            success, image = vidcap.read()
            frameNumber += 1

        os.remove(filename)


def main():
    print("Started. Press Ctrl+c to exit.")

    if not os.path.exists("videosToSplit"):
        os.makedirs("videosToSplit")
        print("Created folder videosToSplit to paste the raw material.")
    if not os.path.exists("screenshots"):
        os.makedirs("screenshots")
        print("Created folder screenshots to paste the images.")

    queue = Queue()
    splitQueue = Queue()

    ss1 = Process(target=screenshotter, args=(queue,))
    p2 = Process(target=writer, args=((queue, splitQueue),))
    p3 = Process(target=writer, args=((queue, splitQueue),))
    splitter1 = Process(target=splitter, args=(splitQueue,))

    ss1.start()
    p2.start()
    p3.start()
    splitter1.start()
    
    try:
        ss1.join()
    except KeyboardInterrupt as e:
        print(e)

    ss1.terminate()
    p2.terminate()
    p3.terminate()
    splitter1.terminate()
    print("Exited successfully.")


if __name__ == "__main__":
    main()