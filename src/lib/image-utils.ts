import * as ImagePicker from 'expo-image-picker';

export interface PickedImage {
  base64: string;
  uri: string;
  width: number;
  height: number;
}

const IMAGE_OPTIONS: ImagePicker.ImagePickerOptions = {
  mediaTypes: ['images'],
  allowsEditing: true,
  aspect: [1, 1],
  quality: 0.7,           // JPEG 70% (matches website convention)
  base64: true,
  exif: false,
};

export async function pickImageFromCamera(): Promise<PickedImage | null> {
  const permission = await ImagePicker.requestCameraPermissionsAsync();
  if (!permission.granted) return null;

  const result = await ImagePicker.launchCameraAsync(IMAGE_OPTIONS);
  if (result.canceled || !result.assets[0]?.base64) return null;

  const asset = result.assets[0];
  return { base64: asset.base64!, uri: asset.uri, width: asset.width, height: asset.height };
}

export async function pickImageFromGallery(): Promise<PickedImage | null> {
  const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
  if (!permission.granted) return null;

  const result = await ImagePicker.launchImageLibraryAsync(IMAGE_OPTIONS);
  if (result.canceled || !result.assets[0]?.base64) return null;

  const asset = result.assets[0];
  return { base64: asset.base64!, uri: asset.uri, width: asset.width, height: asset.height };
}
