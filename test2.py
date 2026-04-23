from pdf2image import convert_from_path
import matplotlib.pyplot as plt
import pdf2image
import cv2
import numpy as np
import pygame
import math
import random

# Initialize Pygame
pygame.init()

# Set up the display
screenx = 1660
screeny = 1300
screen = pygame.display.set_mode((screenx,screeny))
pygame.display.set_caption("Gray Image")


def pageGenerator(pdf_lists):
    pp = R"C:\Users\xbox\Downloads\Release-25.12.0-0\poppler-25.12.0\Library\bin"
    
    for pdf_path in pdf_lists:
        # Get total page count for the current PDF
        info = pdf2image.pdfinfo_from_path(pdf_path, poppler_path=pp)
        total_pages = int(info["Pages"])
        
        for page_num in range(1, total_pages + 1):
            # Convert and yield one page at a time
            page = pdf2image.convert_from_path(
                pdf_path, 
                dpi=300, 
                poppler_path=pp,
                first_page=page_num, 
                last_page=page_num,
                thread_count=8
            )
            # convert_from_path returns a list; yield the first (and only) element
            print(f"Getting page number {page_num} from file {pdf_path}")
            yield np.array(page[0],dtype=np.uint8)

def getBoundingBoxes(image):

    img = np.array(image)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


    # binarize
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)

    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(thresh)

    out  = []
    for i in stats:
        if i[4] > 1000:
            pass
        else:
            #i[0] -= 1
            #i[1] -= 1
            #i[2] += 5
            #i[3] += 5
            
            out.append(i)
    return out
def get_lines(page):
    # Ensure image is binary (0 for white, 1 for black)
    # If using standard grayscale: binary = (img_array < 127).astype(int)
    gray = cv2.cvtColor(page, cv2.COLOR_BGR2GRAY)
    # Sum across the horizontal axis (rows)
    row_sums = np.sum(gray==0,axis=1) # Assuming 0 is black
    
    lines = []
    start_y = None
    
    for y, count in enumerate(row_sums):
        if count > 0 and start_y is None:
            start_y = y  # Found the start of a line
        elif count == 0 and start_y is not None:
            # Found a gap, save the line coordinates
            lines.append((start_y, y))
            start_y = None
            
    # Handle the "Accent-only" line issue
    cleaned_lines = []
    for i in range(len(lines)):
        start, end = lines[i]
        height = end - start
        
        # If the line is suspiciously short (just accents), 
        # merge it with the next line instead of treating it as standalone
        if height < 10 and i + 1 < len(lines):
            next_start, next_end = lines[i+1]
            lines[i+1] = (start, next_end) # Extend next line upward
        else:
            cleaned_lines.append((start, end))
            
    return cleaned_lines

def attachAccents(boundingBoxList):
    # Sort by X to keep things predictable
    boundingBoxList.sort(key=lambda b: b[0])
    
    i = 0
    while i < len(boundingBoxList):
        # x, y, w, h, area
        curr = list(boundingBoxList[i])
        
        j = i + 1
        while j < len(boundingBoxList):
            x, y, w, h, area = boundingBoxList[j]
            
            # 1. Check Horizontal Overlap
            # They overlap if the start of one is before the end of the other
            overlap_x = max(curr[0], x) < min(curr[0] + curr[2], x + w)
            
            # 2. Check Vertical Proximity 
            # Gap is the distance between the bottom of the top box and top of the bottom box
            # We use 0.5 * height of the main character as the threshold
            vertical_gap = abs((y+h) - (curr[1])) 
            is_close_y = vertical_gap < (curr[3] * 0.6)

            if overlap_x and is_close_y:
                # Merge logic
                new_x = min(curr[0], x)
                new_y = min(curr[1], y)
                new_w = max(curr[0] + curr[2], x + w) - new_x
                new_h = max(curr[1] + curr[3], y + h) - new_y
                new_area = curr[4] + area # Sum the areas
                
                curr = [new_x, new_y, new_w, new_h, new_area]
                boundingBoxList.pop(j)
                # No j += 1 here because the next item shifted into index j
            else:
                j += 1
                
        boundingBoxList[i] = curr
        i += 1
        
    return boundingBoxList

def renderPage(img):
    # 1. Convert NumPy array (H, W, C) to a Pygame Surface
    # Note: Pygame expects (W, H), so we transpose the axes
    surface = pygame.surfarray.make_surface(img.swapaxes(0, 1))

    # 2. Scale the entire surface at once instead of pixel-by-pixel
    scaled_surface = pygame.transform.scale(surface, (screenx, screeny))

    # 3. Clear and Draw
    screen.fill((255, 255, 255))
    screen.blit(scaled_surface, (0, 0))
    
    # 4. Update the display once per frame, not per row
    pygame.display.update()
def renderBoundingBoxes(bbList, imgWidth, imgHeight):

    scalex = screenx / imgWidth
    scaley = screeny / imgHeight
    # Draw the hollow rectangles using labels
    for i in bbList:  # skip background
        x, y, w, h, area = i
        c = [random.randint(0,255) for i in range(3)]
        pygame.draw.rect(screen, c, (math.floor(x*scalex), math.floor(y*scaley), math.ceil(w*scalex), math.ceil(h*scaley)), 1)

    # Update the display
    pygame.display.update()
def renderLines(lineList, imgWidth, imgHeight):
    scalex = screenx / imgWidth
    scaley = screeny / imgHeight
    for i in lineList:
        pygame.draw.line(screen, (255,0,0), [0, i[0] * scaley],[screenx, i[0] * scaley])
        pygame.draw.line(screen, (0,0,255), [0, i[1] * scaley],[screenx, i[1] * scaley])
    pygame.display.update()
def merge_small_lines(line_indexes, height_threshold=15):
    if not line_indexes:
        return []
        
    merged = []
    # Start with the first line
    curr_start, curr_end = line_indexes[0]
    
    for i in range(1, len(line_indexes)):
        next_start, next_end = line_indexes[i]
        
        # Calculate gap between lines and height of the current segment
        gap = next_start - curr_end
        curr_height = curr_end - curr_start
        
        # Merge if the line is very thin (accents) OR if they are very close
        if curr_height < height_threshold or gap < 5:
            curr_end = next_end # Extend the current line down
        else:
            merged.append((curr_start, curr_end))
            curr_start, curr_end = next_start, next_end
            
    merged.append((curr_start, curr_end)) # Add the last one
    return merged
def merge_accents_by_midpoint(bb_list):
    # Sort by height descending so we process main letters before small accents
    bb_list.sort(key=lambda x: x[3], reverse=True)
    
    merged_indices = set()
    final_boxes = []

    for i in range(len(bb_list)):
        if i in merged_indices: continue
        
        # x, y, w, h, area
        curr = list(bb_list[i])
        curr_mid_x = curr[0] + (curr[2] / 2)
        
        for j in range(len(bb_list)):
            if i == j or j in merged_indices: continue
            
            target = bb_list[j]
            target_mid_x = target[0] + (target[2] / 2)
            
            # Check if the midpoint of the 'accent' is within the X-bounds of the 'letter'
            # Or if the midpoint of the 'letter' is within the X-bounds of the 'accent'
            is_over = (curr[0]-2 <= target_mid_x <= curr[0] + curr[2]+2) or \
                      (target[0]-2 <= curr_mid_x <= target[0] + target[2]+2)

            if is_over:
                # Expand curr to encompass target
                new_x = min(curr[0], target[0])
                new_y = min(curr[1], target[1])
                new_w = max(curr[0] + curr[2], target[0] + target[2]) - new_x
                new_h = max(curr[1] + curr[3], target[1] + target[3]) - new_y
                
                curr = [new_x, new_y, new_w, new_h, curr[4] + target[4]]
                merged_indices.add(j)
        
        final_boxes.append(curr)
    return final_boxes


pdfList = [
    "genesis_small.pdf"
]

'''
for totalPageCounter, page in enumerate(pageGenerator(pdfList)):
    renderPage(page)
    bbList = getBoundingBoxes(page)
    lineIndexes = get_lines(page)
    renderLines(lineIndexes, page.shape[1], page.shape[0])
    #call a method to merge lines
    merge_small_lines(lineIndexes)
    #call a method to merge accent bounding boxes with the letter
    merge_accents_by_midpoint(bbList)
    renderBoundingBoxes(bbList, page.shape[1], page.shape[0])
'''
for totalPageCounter, page in enumerate(pageGenerator(pdfList)):
    renderPage(page)
    
    # 1. Get raw lines and merge them
    rawLines = get_lines(page)
    lineIndexes = merge_small_lines(rawLines)
    renderLines(lineIndexes, page.shape[1], page.shape[0])
    
    # 2. Get all bounding boxes
    allBBs = getBoundingBoxes(page)
    finalBBs = []

    # 3. Process boxes line by line
    for l_start, l_end in lineIndexes:
        # Get boxes that belong to this line (y-coordinate is within line start/end)
        line_boxes = [bb for bb in allBBs if bb[1] >= l_start - 2 and bb[1] <= l_end + 2]
        
        # Merge accents within this specific line
        merged_line_boxes = merge_accents_by_midpoint(line_boxes)
        finalBBs.extend(merged_line_boxes)

    renderBoundingBoxes(finalBBs, page.shape[1], page.shape[0])

    

if False:
  for i in range(1, num_labels):  # skip background
      x, y, w, h, area = stats[i]

      # filter noise
      if area < 20:
          continue

      glyph = thresh[y:y+h, x:x+w]
      glyphs.append(glyph)
      plt.imshow(glyph)
      plt.show()






# Run the game loop
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

# Quit Pygame
pygame.quit()


#def getPages(pdfLists):
#    pp = R"C:\Users\xbox\Downloads\Release-25.12.0-0\poppler-25.12.0\Library\bin"
#    data = pdf2image.pdfinfo_from_path("genesis_small.pdf", poppler_path=pp)
#    pages = convert_from_path("genesis_small.pdf", dpi=300, poppler_path=pp, thread_count=8,
#                            first_page=1, last_page=1)

'''

The UTF-8 Church Slavonic RealityUnicode has a dedicated block for Cyrillic (U+0400 to U+04FF)
 and an Extended block (U+A640 to U+A69F) specifically for Old Cyrillic/Church Slavonic.
 The "ы" Problem (again): In UTF-8, "ы" is one character (U+044B). 
 If your font splits it, the font is likely using an older "Common" encoding or it's a stylistic choice in the glyph design.The Stacking: 
 To get a character like а with a titlo, you represent it as:Base Character:
   а (U+0430)Combining Titlo: ◌҃ (U+0483)The Result:
     The computer sees two codes but renders one "stack."2. 
     Matching PDF Crops to .TTF (The "OCR-Lite" Approach)Since you want to use .ttf fonts
       for scaling, your "matching" logic would look like this:Generate a Reference Map:
          Render every Church Slavonic character (and common letter+accent combinations)
            from your .ttf font into small images using your Pygame setup.Compare:
              Take a cropped box from your PDF and compare it against your "Reference Map"
                using a simple pixel-difference or Mean Squared Error (MSE).$$MSE = \frac{1}{mn}\sum_{i=0}^{m-1}\sum_{j=0}^{n-1}[I(i,j) - K(i,j)]^2$$Identify: 
                The reference image with the lowest error tells you exactly which UTF-8 string to use.3. The "Vectorizing" Secret WeaponIf you find a character
                  in the PDF that doesn't exist in any modern font, you can use the "Backwards Vectorizing" idea.Tool: fontforge (Python-scriptable).Workflow:
                    1. Take your cleaned, merged character image (like your "ы").2. Use a Python library like potrace to turn the bitmap into a path.
                    3. Inject that path into a new .ttf file at a specific Unicode slot.Why do this? You eventually create
                      a perfect digital clone of the specific Bible you are scanning. You can then distribute that .ttf
                        with your app, ensuring the digital text looks 100% identical to the 16th-century original.

'''