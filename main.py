from PIL import Image, ImageDraw
import colorsys

## DEFINE STUFF
TARGET_DARK_LUMA = 0.26
MAX_DARK_LUMA = 0.45

MIN_LIGHT_LUMA = 0.55
TARGET_LIGHT_LUMA = 0.74

MIN_NORMAL_LUMA = 0.3
TARGET_NORMAL_LUMA = 0.5
MAX_NORMAL_LUMA = 0.7

TARGET_MUTED_SATURATION = 0.3
MAX_MUTED_SATURATION = 0.4

TARGET_VIBRANT_SATURATION = 1
MIN_VIBRANT_SATURATION = 0.35

WEIGHT_SATURATION = 3
WEIGHT_LUMA = 6
WEIGHT_POPULATION = 1



## SORT STUFF

# Calculate inverted difference between value and target
def invert_diff(value, target):
    return 1 - abs(value - target)


# Find the maximum population in the image swatch (ie max number of pixels in image using that color)
def find_max_population(colors):
    return max([c[0] for c in colors])


# Calculate mean of values weighted against targets
def weighted_mean(values):
    total = 0
    sumWeight = 0
    i = 0
    while i < len(values):
        value = values[i]
        weight = values[i + 1]
        
        total += value * weight
        sumWeight += weight
        
        i += 2
        
    return total / sumWeight


# Calculate value to compare suitability of image swatch colors
def create_comparison_value(saturation, targetSaturation,
    luma, targetLuma, population, maxPopulation):
    return weighted_mean([
        invert_diff(saturation, targetSaturation), WEIGHT_SATURATION,
        invert_diff(luma, targetLuma), WEIGHT_LUMA,
        population / maxPopulation, WEIGHT_POPULATION
        ])

    
# Check if a color has already been used in the material swatch
def is_already_selected(swatch_dict, swatch):
    return swatch in swatch_dict.values()
    

#Find color in image swatch best matching the criteria passed as arguments
def findColorVariation(colors, swatch_dict, targetLuma, minLuma, maxLuma, targetSaturation, minSaturation, maxSaturation):
    
    max_value = 0
    chosen = None
    
    highest_population = find_max_population(colors)

    for c in colors:
        sat = swatch_to_hsl(c)[1][1]
        #print("Sat: ", str(sat))
        luma = swatch_to_hsl(c)[1][2]
        #print("Luma: ", str(luma))
        pop = c[0]
        #print("pop: ", str(pop))

        if sat >= minSaturation and sat <= maxSaturation and luma >= minLuma and luma <= maxLuma and not is_already_selected(swatch_dict, c):
            
            #print("Swatch meets initial criteria. Considering...")
            value = create_comparison_value(sat, targetSaturation, luma, targetLuma, pop, highest_population)
            
            if value > max_value:
                chosen = c
                max_value = value
                
                #print("Swatch is new best. Adding to consideration.")
    
    return chosen


# Generate a new color by changing luminosity of a reference
def generate_luma(reference, target_luma):
    
        hsl = swatch_to_hsl(reference)
        hsl_new = (hsl[0], (hsl[1][0], hsl[1][1], target_luma, 0))
        
        return hsl_to_swatch(hsl_new)


# Take a triad of colors (light, dark, normal), and fill in any missing
def fill_set(swatch, keys, targets):
    
    color_set = [ swatch[k] for k in keys ]
    
    for p, color in enumerate(color_set):
        print(color)
        if color is None:
            print("Missing color found")
            for i in range(1,3):
                if color_set[p-i] is not None:
                    swatch[keys[p]] = generate_luma(color_set[p-i], targets[p])
                    print(color)
                    break


# Fill in all missing colors across material swatch
def fill_swatch(swatch):
    
    fill_set(swatch, ("v_dark", "v_light", "vibrant"), (TARGET_DARK_LUMA, TARGET_LIGHT_LUMA, TARGET_NORMAL_LUMA))
    fill_set(swatch, ("m_dark", "m_light", "muted"), (TARGET_DARK_LUMA, TARGET_LIGHT_LUMA, TARGET_NORMAL_LUMA))
        
    return swatch


# Build material swatch and save file
def build_swatch(colors, savefile = True):
    picked_swatch = {}
    
    picked_swatch["vibrant"] = findColorVariation(colors, picked_swatch, TARGET_NORMAL_LUMA, MIN_NORMAL_LUMA, MAX_NORMAL_LUMA, TARGET_VIBRANT_SATURATION, MIN_VIBRANT_SATURATION, 1)

    picked_swatch["v_light"] = findColorVariation(colors, picked_swatch, TARGET_LIGHT_LUMA, MIN_LIGHT_LUMA, 1, TARGET_VIBRANT_SATURATION, MIN_VIBRANT_SATURATION, 1)

    picked_swatch["v_dark"] = findColorVariation(colors, picked_swatch, TARGET_DARK_LUMA, 0, MAX_DARK_LUMA, TARGET_VIBRANT_SATURATION, MIN_VIBRANT_SATURATION, 1)
    
    picked_swatch["muted"] = findColorVariation(colors, picked_swatch, TARGET_NORMAL_LUMA, MIN_NORMAL_LUMA, MAX_NORMAL_LUMA, TARGET_MUTED_SATURATION, 0, MAX_MUTED_SATURATION)

    picked_swatch["m_light"] = findColorVariation(colors, picked_swatch, TARGET_LIGHT_LUMA, MIN_LIGHT_LUMA, 1, TARGET_MUTED_SATURATION, 0, MAX_MUTED_SATURATION)

    picked_swatch["m_dark"] = findColorVariation(colors, picked_swatch, TARGET_DARK_LUMA, 0, MAX_DARK_LUMA, TARGET_MUTED_SATURATION, 0, MAX_MUTED_SATURATION)
    
    print(picked_swatch)
    
    filled_swatch = fill_swatch(picked_swatch)
    print(filled_swatch)
    
    if savefile:
        save_swatch("swatch_material.png", filled_swatch.values(), swatchsize=20)

    return filled_swatch


## GET IMAGE AND BUILD INITIAL PALETTE

def get_colors(infile, numcolors=64, resize=200):

    image = Image.open(infile)
    image = image.resize((resize, resize))
    result = image.convert('P', palette=Image.ADAPTIVE, colors=numcolors)
    result.putalpha(0)
    
    colors = result.getcolors(resize*resize)
    return colors


def save_swatch(outfile, colors, swatchsize=20):
    # Save colors to file
    
    pal = Image.new('RGB', (swatchsize*len(colors), swatchsize))
    draw = ImageDraw.Draw(pal)
    
    posx = 0
    for count, col in colors:
        draw.rectangle([posx, 0, posx+swatchsize, swatchsize], fill=col)
        posx = posx + swatchsize
    
    del draw
    pal.save(outfile, "PNG")


def swatch_to_hsl(color):
    return (color[0], (*colorsys.rgb_to_hsv(*[v/255 for v in color[1][:-1]]), 0))

def hsl_to_swatch(color):
    return (color[0], (*[int(c * 255) for c in colorsys.hsv_to_rgb(*[v for v in color[1][:-1]]) ], 0))


if __name__ == '__main__':
    colors = get_colors('infile.jpg')
    
    save_swatch('swatch_image.png', colors)
    
    build_swatch(colors, savefile = True)