/**
 * Ambient type mappings for Deck.gl v8 packages.
 * Deck.gl v8 stores TypeScript declarations under the 'typed' subpath
 * without exporting them from the package root.
 */
declare module '@deck.gl/core' {
  export * from '@deck.gl/core/typed';
}

declare module '@deck.gl/layers' {
  export * from '@deck.gl/layers/typed';
}

declare module '@deck.gl/mapbox' {
  export * from '@deck.gl/mapbox/typed';
}

declare module '@deck.gl/geo-layers' {
  export * from '@deck.gl/geo-layers/typed';
}

declare module '@deck.gl/react' {
  export * from '@deck.gl/react/typed';
}
