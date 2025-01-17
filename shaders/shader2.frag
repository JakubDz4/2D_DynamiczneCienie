#version 330 core

out vec4 fragColor;

uniform float uRepeat;

void main()
{
    float val = 1.0/uRepeat;
    fragColor = vec4(val);
}
