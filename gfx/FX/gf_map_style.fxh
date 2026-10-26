PixelShader =
{
Code
[[
// GF-MAP dark political map, 2026-10-19.
// Display transforms only: national color definitions and geographic data are unchanged.
static const float GF_MAP_EXPOSURE = 0.74f;
static const float GF_WATER_EXPOSURE = 0.76f;
static const float3 GF_BORDER_CORE = float3(0.94f, 0.975f, 1.0f);
static const float3 GF_BORDER_HALO = float3(0.66f, 0.79f, 0.92f);

// Only LAND POLITICAL FILL changes with zoom: native near fill, styled far fill.
// Never apply this weight to overall lighting, water exposure, borders or model visibility.
static const float GF_LAND_FILL_NEAR_HEIGHT = 260.0f;
static const float GF_LAND_FILL_FAR_HEIGHT = 350.0f;

float GFMapLandFillWeight()
{
    return smoothstep(GF_LAND_FILL_NEAR_HEIGHT, GF_LAND_FILL_FAR_HEIGHT, vCamPos.y);
}

float GFMapPoliticalChannel(out float3 Color, float3 Background,
    float CameraDistance, float2 UV, in sampler2D DistanceTexture,
    in sampler2D ControlTexture, float OutlineCutoff, float Strength,
    out float2 BorderLight)
{
    float2 Control = tex2D(ControlTexture, UV).bg;
    float Pulse = (sin(vGlobalTime * 3.5f) + 1.0f) * 0.5f;
    Strength *= lerp(lerp(0.45f, 1.0f, 1.0f - Control.r), 1.0f, Pulse);

    float4 Field = gradient_border_multisample_alpha(
        tex2D(DistanceTexture, UV), DistanceTexture, UV);
    // Use the center color, so multisampling the distance field does not
    // introduce a broad blend between neighboring countries' colors.
    float3 PoliticalColor = tex2D(DistanceTexture, UV).rgb;
    float Fill = gradient_border_distance_to_alpha(
        Levels(Field.a, 0.0f, OutlineCutoff), CameraDistance);
    float CameraFade = cam_distance(90.0f, 420.0f);
    Fill = max(Fill, lerp(0.93f, 0.992f, CameraFade));
    Color = lerp(Background, PoliticalColor, saturate(Fill * Strength));

    // Distance-field core and halo are shaded after terrain lighting.
    // No dark strip or broad national-color edge gradient remains.
    float Core = smoothstep(OutlineCutoff - 0.002f,
        OutlineCutoff + 0.009f, Field.a);
    float Halo = smoothstep(OutlineCutoff - 0.019f,
        OutlineCutoff + 0.003f, Field.a);
    BorderLight = float2(Core, Halo) * saturate(Strength) * Control.g;
    return saturate(Fill * Strength) * Control.g;
}

void GFMapApplyPoliticalColor(inout float3 Color, float3 Normal, float2 UV,
    in sampler2D DistanceTexture, in sampler2D ControlTexture,
    float2 OutlineCutoff, float2 CameraOverride,
    inout float BloomAlpha, out float2 BorderLight)
{
    BorderLight = float2(0.0f, 0.0f);
#ifndef GRADIENT_BORDERS
    BloomAlpha = 1.0f;
    return;
#else
    float Style = GFMapLandFillWeight();
    float3 NativeColor = Color;
    float NativeBloomAlpha = BloomAlpha;
    if (Style < 1.0f)
    {
        gradient_border_apply(NativeColor, Normal, UV, DistanceTexture, ControlTexture,
            1.0f, OutlineCutoff, CameraOverride, NativeBloomAlpha);
        if (Style <= 0.0f)
        {
            Color = NativeColor;
            BloomAlpha = NativeBloomAlpha;
            return;
        }
    }
    float CameraDistance = gradient_border_camera_distance();
    float Camera1 = saturate(CameraDistance * int(1.0f - CameraOverride.x)
        + CameraOverride.x);
    float Camera2 = saturate(CameraDistance * int(1.0f - CameraOverride.y)
        + CameraOverride.y);
    float HalfPixel = 0.5f / GB_TextureHeight;
    UV.y *= 0.5f - HalfPixel;
    float2 UV2 = float2(UV.x, UV.y + 0.5f);
    float3 ChannelColor;
    float2 Border1;
    float2 Border2;
    float Alpha1 = GFMapPoliticalChannel(ChannelColor, Color, Camera1,
        UV, DistanceTexture, ControlTexture, OutlineCutoff.x,
        GB_STRENGTH_CH1, Border1);
    float Transparency1 = tex2D(ControlTexture, UV).g;
    Color = lerp(Color, ChannelColor, Transparency1);

    float Alpha2 = GFMapPoliticalChannel(ChannelColor, Color, Camera2,
        UV2, DistanceTexture, ControlTexture, OutlineCutoff.y,
        (1.0f - Alpha1 * GB_STRENGTH_CH1 * GB_FIRST_LAYER_PRIORITY)
        * GB_STRENGTH_CH2, Border2);
    float Transparency2 = tex2D(ControlTexture, UV2).g;
    Color = lerp(Color, ChannelColor, Transparency2);
    // Typed border ribbons own emission, so coasts and DMZ have no white underlay.
    BorderLight = float2(0.0f, 0.0f);
    BloomAlpha = 1.0f - max(Alpha1, Alpha2);
    if (Style < 1.0f)
    {
        Color = lerp(NativeColor, Color, Style);
        BloomAlpha = lerp(NativeBloomAlpha, BloomAlpha, Style);
    }
#endif
}

float3 GFMapReliefLighting(float3 PoliticalColor, float3 ReliefNormal)
{
    // Only height-derived normals affect political shading. Tiled grass,
    // forest and desert textures cannot tint distant national fills.
    float3 ReliefDirection = normalize(float3(-0.55f, 0.72f, -0.42f));
    float Relief = clamp(0.98f + 0.52f * dot(
        ReliefNormal - float3(0.0f, 1.0f, 0.0f), ReliefDirection),
        0.66f, 1.22f);
    return PoliticalColor * Relief;
}

float3 GFMapBorderLighting(float3 Color, float2 BorderLight)
{
    // Explicit halo remains visible when the user's postfx option is off.
    Color += GF_BORDER_HALO * BorderLight.y * 0.19f;
    return lerp(Color, GF_BORDER_CORE * 1.10f,
        saturate(BorderLight.x * 0.94f));
}
]]
}
