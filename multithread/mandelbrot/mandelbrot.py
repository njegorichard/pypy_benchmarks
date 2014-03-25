from common.abstract_threading import Future, atomic
import Image, sys


def calculate(a, b, im_size, max_iter=255):
    print "a:%s, b:%s, im_size:%s" % (a, b, im_size)
    ar, ai = a
    br, bi = b
    width, height = im_size
    imag_step = (bi - ai) / (height - 1)
    real_step = (br - ar) / (width - 1)
    print "real/width:%s, imag/height:%s" % (real_step, imag_step)

    with atomic:
        result = [[0] * width for y in xrange(height)]
    for y in xrange(height):
        zi = ai + y * imag_step
        for x in xrange(width):
            zr = ar + x * real_step
            z = complex(zr, zi)
            c = z
            for i in xrange(max_iter):
                if abs(z) > 2.0:
                    break
                z = z * z + c
            result[y][x] = i

    return result

def save_img(image, file_name='out.png'):
    im = Image.new("RGB", (len(image[0]), len(image)))
    out = im.load()

    for y in xrange(len(image)):
        for x in xrange(len(image[0])):
            c = image[y][x]
            out[x,y] = c, c, c
    im.save(file_name, 'PNG')

def save_to_file(image, file_name='out.txt'):
    with atomic:
        s = "\n".join(map(str, image))
    with open(file_name, 'w') as f:
        f.write(s)


def merge_imgs(imgs):
    res = []
    for img in imgs:
        for y in img:
            res.append(y)
    return res


def run(threads=2):
    threads = int(threads)
    ar, ai = -2.0, -1.5
    br, bi = 1.0, 1.5
    width, height = 4096, 4096

    step = (bi - ai) / threads
    res = []
    ai = -1.5
    bi = ai + step
    for i in xrange(threads):
        res.append(Future(calculate,
                          a=(ar, ai + i * step),
                          b=(br, bi + i * step),
                          im_size=(width, int(height / threads))
            ))

    res = [f() for f in res]
    return merge_imgs(res)



if __name__ == '__main__':
    image = run(int(sys.argv[1]))
    save_to_file(image)
    # save_img(image) don't run on STM, allocates 4000GB of memory
