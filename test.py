import pygame
import unicodedata


# Initialize Pygame
pygame.init()
# Set up display dimensions
width = 800
height = 600
screen = pygame.display.set_mode((width, height))
# Load a Church Slavonic font
font_path = "Ponomar-Regular.ttf"
church_slavonic_font = pygame.font.Font(font_path, 48)


with open("test.txt", "r", encoding="utf-8") as f:
    text = f.read()
    text = unicodedata.normalize("NFC", text)
    
    print([hex(ord(c)) for c in text[:20]])
print(text)

# Main game loop
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
    # Clear screen with black
    screen.fill((0, 0, 0))
    # Render text using Church Slavonic font
    text_surface = church_slavonic_font.render("O%,58&M		',6''1EB", True, (255, 255, 255))
    text_rect = text_surface.get_rect(center=(width//2, height//2))
    screen.blit(text_surface, text_rect)
    # Update display
    pygame.display.flip()
# Quit Pygame
pygame.quit()