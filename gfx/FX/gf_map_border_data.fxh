PixelShader =
{
Code
[[
// Continuous alpha-only control fields. RGB channel order and color space
// must never decide whether a border is a country, state or province line.
static const float GF_BORDER_DATA_WIDTH = 2048.0f;
static const float GF_BORDER_DATA_HEIGHT = 1024.0f;
static const float GF_BORDER_PROFILE_START = 128.0f;
static const float GF_BORDER_MASK_START = 256.0f;
static const float GF_BORDER_MASK_SCALE = 4.0f;

float4 GFBorderDataTexel(in sampler2D DataTexture, float Column, float Row)
{
    float2 DataUV = float2((Column + 0.5f) / GF_BORDER_DATA_WIDTH,
        (Row + 0.5f) / GF_BORDER_DATA_HEIGHT);
    return tex2Dlod(DataTexture, float4(DataUV, 0.0f, 0.0f));
}

float4 GFBorderReadProfile(in sampler2D DataTexture, float2 LineUV,
    float3 WorldPosition, out float BorderType, out float IsInland)
{
    BorderType = 0.0f;
    IsInland = 0.0f;
    // Broad uniform metadata bands tolerate interpolation and RGB swizzling.
    float Marker = floor(GFBorderDataTexel(DataTexture, 16.0f, 8.0f).a * 255.0f + 0.5f);
    if (abs(Marker - 253.0f) > 0.5f)
    {
        // Only unmodified stock textures can enter the native sampling path.
        return tex2D(DataTexture, LineUV);
    }

    float TypeCode = floor(GFBorderDataTexel(DataTexture, 16.0f, 24.0f).a * 255.0f + 0.5f);
    float ProfileWidth = floor(GFBorderDataTexel(DataTexture, 16.0f, 40.0f).a * 255.0f + 0.5f) * 2.0f;
    float ProfileHeight = floor(GFBorderDataTexel(DataTexture, 16.0f, 56.0f).a * 255.0f + 0.5f);
    if (TypeCode < 0.5f || TypeCode > 3.5f || ProfileWidth < 8.0f
        || ProfileWidth > 256.5f || ProfileHeight < 7.5f || ProfileHeight > 128.5f)
    {
        // Never draw metadata or the land mask as a repeating line texture.
        return float4(0.0f, 0.0f, 0.0f, 0.0f);
    }
    BorderType = TypeCode;

    float PixelX = fmod(floor(WorldPosition.x) + MAP_SIZE_X, MAP_SIZE_X);
    float PixelY = clamp(MAP_SIZE_Y - 1.0f - floor(WorldPosition.z),
        0.0f, MAP_SIZE_Y - 1.0f);
    float MaskX = floor(PixelX / GF_BORDER_MASK_SCALE);
    float MaskY = floor(PixelY / GF_BORDER_MASK_SCALE);
    float MaskAlpha = GFBorderDataTexel(DataTexture, MaskX,
        GF_BORDER_MASK_START + MaskY).a;
    IsInland = step(0.99f, MaskAlpha);

    float2 ProfileUV = float2(
        (0.5f + frac(LineUV.x) * (ProfileWidth - 1.0f)) / GF_BORDER_DATA_WIDTH,
        (GF_BORDER_PROFILE_START + 0.5f + saturate(LineUV.y)
            * (ProfileHeight - 1.0f)) / GF_BORDER_DATA_HEIGHT);
    return tex2Dlod(DataTexture, float4(ProfileUV, 0.0f, 0.0f));
}
]]
}
