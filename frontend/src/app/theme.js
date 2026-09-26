import {createTheme} from '@mantine/core';

// Omen blue, #357ABF, is the header colour of the previous Omen Assessors site and
// sits at shade 6. Ink, the deepest shade, is used for text and headings.
const omen = ['#eaf2fa', '#d3e3f3', '#a8c7e8', '#7aa9dc', '#5391d1', '#3f84c8', '#357abf', '#2a67a6', '#205487', '#16324f'];

export const TOKENS = {blue: '#357abf', ink: '#16324f', slate: '#5b6b7c', paper: '#f3f6f9', approved: '#2e7d4f', refused: '#b42318'};

// A system font stack, deliberately: assessors open this on phones at property
// sites with poor signal, so the interface never waits on a web font download.
const system = "system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif";

export const theme = createTheme({
  primaryColor: 'omen',
  primaryShade: 6,
  colors: {omen},
  black: TOKENS.ink,
  fontFamily: system,
  headings: {fontFamily: system, fontWeight: '650', sizes: {h1: {fontSize: '1.75rem', lineHeight: '1.25'}, h2: {fontSize: '1.25rem', lineHeight: '1.35'}, h3: {fontSize: '1.05rem', lineHeight: '1.4'}}},
  defaultRadius: 'sm',
  radius: {xs: '2px', sm: '4px', md: '8px', lg: '12px', xl: '16px'},
  components: {
    Button: {defaultProps: {radius: 'sm'}},
    TextInput: {defaultProps: {radius: 'sm'}},
    Select: {defaultProps: {radius: 'sm'}},
    Paper: {defaultProps: {radius: 'md'}},
    Table: {defaultProps: {verticalSpacing: 'sm', highlightOnHover: true}},
  },
});
