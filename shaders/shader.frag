#version 330 core

out vec4 fragColor;

uniform float uVisibility;

void main()
{
    fragColor = vec4(uVisibility, uVisibility, 0.0, 1.0);
}
